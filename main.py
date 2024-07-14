# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import bpy
import os
import math
import json

bl_info = {
    "name": "Weapon Builder",
    "author": "Stewie",
    "description": "Add Attachments to Weapons",
    "blender": (4, 1, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Object"
}

class STLLoaderPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    stl_path: bpy.props.StringProperty(
        name="STL Path",
        description="Path to your STL files directory",
        subtype='DIR_PATH',
        default=""
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "stl_path")

# Function to list STL files in the Weapons directory
def get_weapon_files(self, context):
    preferences = context.preferences.addons[__name__].preferences
    stl_path = preferences.stl_path
    weapons_folder = os.path.join(stl_path, "Weapons")
    
    stl_files = []
    for root, dirs, files in os.walk(weapons_folder):
        for file in files:
            if file.endswith('.stl'):
                full_path = os.path.join(root, file)
                stl_files.append((full_path, file, ""))
    
    return stl_files

def get_attachment_files(self, context):
    preferences = context.preferences.addons[__name__].preferences
    stl_path = preferences.stl_path
    attachments_folder = os.path.join(stl_path , "Attachments")
    
    blend_files = [("None", "None", "")]
    for root, dirs, files in os.walk(attachments_folder):
        for file in files:
            if file.endswith('.stl'):
                full_path = os.path.join(root, file)
                blend_files.append((full_path, file, ""))
    
    return blend_files

# Function to list attachment points from the .blend file
def get_attachment_points():
    # Dictionary to store start and end points
    start_points = {}
    end_points = {}
    single_points =[]

    # Loop through objects
    for obj in bpy.data.objects:
        # Only care about EMPTY
        if obj.type == 'EMPTY':
            if "Start" in obj.name:
                # Extract the rail name (assuming the format is consistent and "Start" is at the end)
                rail_name = obj.name.replace(" Start", "")
                start_points[rail_name] = obj.name
            elif "End" in obj.name:
                # Extract the rail name (assuming the format is consistent and "End" is at the end)
                rail_name = obj.name.replace(" End", "")
                end_points[rail_name] = obj.name
            elif "Muzzle" in obj.name:
                #Muzzle is just a single point no start and end
                point_name = obj.name
                single_points.append(point_name)
            elif "Mag" in obj.name:
                #Muzzle is just a single point no start and end
                point_name = obj.name
                single_points.append(point_name)

    # Find pairs of start and end points
    attachment_points = []
    for rail_name in start_points:
        if rail_name in end_points:
            attachment_points.append(rail_name)
    for point in single_points:
            attachment_points.append(point)
    return sorted(attachment_points)

#helper function for handling attachment properties dynamicaly
def update_dynamic_properties(context):
    unregister_dynamic_properties(context)
    register_dynamic_properties(context)

def register_dynamic_properties(context):
    attachment_points = get_attachment_points()
    for point in attachment_points:
        prop_name = f"attachment_file_list_{point}"
        setattr(bpy.types.Scene, prop_name, bpy.props.EnumProperty(items=get_attachment_files))

def unregister_dynamic_properties(context):
    attachment_points = get_attachment_points()
    for point in attachment_points:
        prop_name = f"attachment_file_list_{point}"
        if hasattr(bpy.types.Scene, prop_name):
            delattr(bpy.types.Scene, prop_name)

class SetSTLPathOperator(bpy.types.Operator, bpy.types.OperatorFileListElement):
    bl_idname = "object.set_stl_path"
    bl_label = "Set STL Path"
    
    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        preferences = context.preferences.addons[__name__].preferences
        preferences.stl_path = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class STLLoaderPanel(bpy.types.Panel):
    bl_label = "Weapon STL Loader"
    bl_idname = "OBJECT_PT_stl_loader"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'STLLoader'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Select Weapon STL File")
        layout.prop(context.scene, 'stl_file_list')
        layout.operator("object.load_weapon_stl")

        attachment_points = get_attachment_points()
        layout.label(text=f"{attachment_points}")
        # Retrieve attachment points
        for point in attachment_points:
            prop_name = f"attachment_file_list_{point}"
            layout.label(text=f"{point}")
            layout.prop(context.scene, prop_name)

        layout.operator("object.load_attachments", text="Load All Attachments")

class LoadWeaponSTLOperator(bpy.types.Operator):
    bl_idname = "object.load_weapon_stl"
    bl_label = "Load Weapon STL"

    def execute(self, context):
        stl_file = context.scene.stl_file_list
        self.load_weapon_stl(stl_file,context)
        update_dynamic_properties(context)
        return {'FINISHED'}

    def load_weapon_stl(self, stl_file,context):
        preferences = context.preferences.addons[__name__].preferences
        STL_PATH = preferences.stl_path
        weapons_folder = os.path.join(STL_PATH, "Weapons")
        stl_path = os.path.join(weapons_folder, stl_file)
        blend_path = os.path.splitext(stl_path)[0] + '.blend'
        json_path = os.path.splitext(stl_path)[0] + '.json'

        if not os.path.exists(stl_path):
            self.report({'ERROR'}, f"STL file {stl_file} not found in Weapons folder.")
            return {'CANCELLED'}

        # Delete existing objects in the scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

        # Import STL
        bpy.ops.import_mesh.stl(filepath=stl_path)

        # Apply transformations if JSON exists
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)

            weapon_data = data.get("weapon", {})
            rotation = weapon_data.get("rotation", [0, 0, 0])

            # Get the imported object (assuming it's the active object)
            obj = bpy.context.object

            # Apply rotation
            obj.rotation_euler = (
                math.radians(rotation[0]),
                math.radians(rotation[1]),
                math.radians(rotation[2])
            )

            # Set origin to center of mass
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')

            # Move the object to (0, 0, 0)
            obj.location = (0, 0, 0)

            # Load reference points from blend file if it exists
            if os.path.exists(blend_path):
                with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                    data_to.objects = [name for name in data_from.objects]

                for obj in data_to.objects:
                    if obj is not None and obj.type == 'EMPTY':
                        bpy.context.collection.objects.link(obj)
        
                self.report({'INFO'}, f"Attachment Points loaded for STL file {stl_file}")

        return {'FINISHED'}

class LoadAttachmentsOperator(bpy.types.Operator):
    bl_idname = "object.load_attachments"
    bl_label = "Load All Attachments"

    def execute(self, context):
        self.clear_attachments_collection(context)
        attachment_points = get_attachment_points()
        for point in attachment_points:
            prop_name = f"attachment_file_list_{point}"
            stl_file = getattr(context.scene, prop_name)
            
            if stl_file != "None":
                self.load_attachment(stl_file,point,context)

        return {'FINISHED'}

    def clear_attachments_collection(self, context):
        collection_name = "Attachments"
        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
            # Deselect all objects
            bpy.ops.object.select_all(action='DESELECT')
            # Select all objects in the collection
            for obj in collection.objects:
                obj.select_set(True)
            # Delete selected objects
            bpy.ops.object.delete()
            # Remove the collection
            bpy.data.collections.remove(collection)
        
        # Create a new "Attachments" collection
        attachments_collection = bpy.data.collections.new(collection_name)
        context.scene.collection.children.link(attachments_collection)

    def load_attachment(self,attachment_file,point,context):
        preferences = context.preferences.addons[__name__].preferences
        STL_PATH = preferences.stl_path
        attachments_folder = os.path.join(STL_PATH, "Attachments")
        stl_path = os.path.join(attachments_folder, attachment_file)
        blend_path = os.path.splitext(stl_path)[0] + '.blend'
        attachment_filename = os.path.basename(attachment_file)

        if not os.path.exists(blend_path):
            self.report({'ERROR'}, f"Blend file {attachment_file} not found in Attachments folder.")
            return {'CANCELLED'}

        if not os.path.exists(stl_path):
            self.report({'ERROR'}, f"STL file {stl_path} not found in Attachments folder.")
            return {'CANCELLED'}

        # Load attachment from blend file
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            data_to.objects = [name for name in data_from.objects]

        attachments_collection = bpy.data.collections.get("Attachments")

        # Link the objects to the "Attachments" collection
        for obj in data_to.objects:
            if obj is not None:
                attachments_collection.objects.link(obj)

        # Import the corresponding STL file and move to "Attachments" collection
        bpy.ops.import_mesh.stl(filepath=stl_path)
        stl_objects = bpy.context.selected_objects
        
        for obj in stl_objects:
            attachments_collection.objects.link(obj)
            if obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(obj)

        # Find the attachment empty and STL object
        attachment_empty = None
        for obj in bpy.data.objects:
            if obj.type == 'EMPTY' and obj.name.startswith(os.path.splitext(attachment_filename)[0]):
                attachment_empty = obj
                break

        if not attachment_empty:
            self.report({'ERROR'},f"Attachment Empty object not found. Should start with: {os.path.splitext(attachment_filename)[0]}")
            return {'CANCELLED'}

        stl_object = None
        for obj in stl_objects:
            if obj != attachment_empty:
                stl_object = obj
                break

        if not stl_object:
            self.report({'ERROR'}, "STL object not found.")
            return {'CANCELLED'}
        
        # Set origin to center of mass
        bpy.context.view_layer.objects.active = stl_object
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
        
        # Parent the STL object to the empty object
        stl_object.parent = attachment_empty
        # move back after setting parent
        stl_object.matrix_parent_inverse = attachment_empty.matrix_world.inverted()

        # Position the attachment correctly
        self.position_attachment(attachment_empty, attachment_file,point)
        
        self.report({'INFO'}, f"Attachment {attachment_file} loaded successfully")

        return {'FINISHED'}
    
    def position_attachment(self, attachment_empty, attachment_file,point):
        # Find the rail start and end points
        if "Muzzle" in point:
            # For Muzzle type attachment points, use only one point
            rail_start = bpy.data.objects.get(f"{point}")
            rail_end = rail_start  # Use the same point for both start and end
        elif "Mag" in point:
            # For Mag type attachment points, use only one point
            rail_start = bpy.data.objects.get(f"{point}")
            rail_end = rail_start  # Use the same point for both start and end
        else:
            rail_start = bpy.data.objects.get(f"{point} Start")
            rail_end = bpy.data.objects.get(f"{point} End")
        
        if not rail_start or not rail_end:
            self.report({'ERROR'}, "Rail start or end point not found.")
            return {'CANCELLED'}

        # Calculate the midpoint between the rail start and end points
        midpoint = (rail_start.location + rail_end.location) / 2

        # Calculate the offset to align the attachment correctly
        offset = attachment_empty.matrix_world.translation - midpoint

        # Apply the calculated offset
        attachment_empty.location -= offset

        # Calculate the direction vector of the rail
        rail_rotation_euler = rail_start.rotation_euler

        # Set the attachment's rotation to match the rail's rotation
        attachment_empty.rotation_euler = rail_rotation_euler



        self.report({'INFO'}, f"Attachment {attachment_file} positioned and rotated successfully at {point}")
        return {'FINISHED'}
    
def register():
    bpy.utils.register_class(STLLoaderPreferences)
    bpy.utils.register_class(STLLoaderPanel)
    bpy.utils.register_class(LoadWeaponSTLOperator)
    bpy.utils.register_class(LoadAttachmentsOperator)
    bpy.utils.register_class(SetSTLPathOperator)
    bpy.types.Scene.stl_file_list = bpy.props.EnumProperty(items=get_weapon_files)
    bpy.types.Scene.stl_path = bpy.props.StringProperty(name="STL Path", subtype='DIR_PATH')

def unregister():
    bpy.utils.unregister_class(STLLoaderPreferences)
    bpy.utils.unregister_class(STLLoaderPanel)
    bpy.utils.unregister_class(LoadWeaponSTLOperator)
    bpy.utils.unregister_class(LoadAttachmentsOperator)
    bpy.utils.unregister_class(SetSTLPathOperator)
    del bpy.types.Scene.stl_file_list
    del bpy.types.Scene.stl_path

if __name__ == "__main__":
    register()