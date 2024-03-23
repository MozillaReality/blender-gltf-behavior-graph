import bpy
from bpy.types import NodeCustomGroup
from bpy.types import Operator
from mathutils import Vector
from .nodes import BGNode

class BGNodeGroup(NodeCustomGroup):
    bl_idname = "BGNodeGroup"
    bl_label = "Node Group"

    def draw_buttons(self, context, layout):
        if (self == self.id_data.nodes.active):
            row = layout.row(align=True)
            row.prop(self, "node_tree", text="")
            row.operator("bg.toggle_edit_group", text="", icon='NODETREE')

    def free(self):
        self.node_tree.unregister_all_objects()


class BGGroupNodesOperator(Operator):
    """Create a node group from the selected nodes"""
    bl_idname = "bg.group_nodes"
    bl_label = "Group BG Nodes"

    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        if hasattr(space_data, "node_tree"):
            if (space_data.node_tree):
                return space_data.tree_type == "BGTree"
        return False

    def execute(self, context):
        space_data = context.space_data
        path = space_data.path
        base_node_tree = path[-1].node_tree
        node_group = bpy.data.node_groups.new("BGNodeGroup", "BGTree")

        # Get the selected nodes (excluding any group inputs/outputs).
        selected_nodes = []
        nodes_count = 0
        for node in base_node_tree.nodes:
            if node.bl_idname in ['NodeGroupInput', 'NodeGroupOutput']:
                node.select = False
            if node.select:
                selected_nodes.append(node)
                nodes_count += 1

        # Get any links that link outside the selection..
        external_links = {
            "inputs": [],
            "outputs": []
            }
        for node in selected_nodes:
            for node_input in node.inputs:
                if node_input.is_linked:
                    link = node_input.links[0]
                    if not link.from_node in selected_nodes:
                        if not link in external_links["inputs"]:
                            external_links["inputs"].append(link)
            for node_output in node.outputs:
                if node_output.is_linked:
                    for link in node_output.links:
                        if not link.to_node in selected_nodes:
                            if not link in external_links["outputs"]:
                                external_links["outputs"].append(link)

        # Find the center of the node group and how much space it needs.
        group_min_x = 0
        group_max_x = 0
        group_center = Vector((0, 0))
        for node in selected_nodes:
            group_center += node.location / nodes_count
            if node.location.x < group_min_x:
                group_min_x = node.location.x
            if node.location.x > group_max_x:
                group_max_x = node.location.x

        # Add group input and output nodes for the new node group
        group_input_node = node_group.nodes.new("NodeGroupInput")
        group_output_node = node_group.nodes.new("NodeGroupOutput")
        group_input_node.location = Vector((group_min_x - 200, group_center.y))
        group_output_node.location = Vector((group_max_x + 200, group_center.y))

        # Copy the selected nodes for later pasting into the group.
        if nodes_count > 0:
            bpy.ops.node.clipboard_copy()

        # Create the new group node.
        group_node = base_node_tree.nodes.new("BGNodeGroup")
        group_node.location = group_center
        group_node.node_tree = node_group

        # Switch the editor to view the group node.
        path.append(node_group, node=group_node)

        # Paste the copied nodes into the group.
        if nodes_count > 0:
            bpy.ops.node.clipboard_paste()

        # Reattach all the links to group inputs and outputs.
        for link in external_links["inputs"]:
            link_node = node_group.nodes[link.to_node.name]
            node_input = link_node.inputs[link.to_socket.name]

            node_group.links.new(
                group_node.outputs.new(link.to_socket.bl_idname, link.to_socket.name, identifier=link.to_socket.identifier),
                node_input
                )



        for link in external_links["outputs"]:
            link_node = node_group.nodes[link.from_node.name]
            node_output = link_node.outputs[link.from_socket.name]

            node_group.links.new(
                group_node.inputs.new(link.from_socket.bl_idname, link.from_socket.name, identifier=link.from_socket.identifier),
                node_output
                )


        for x, link in enumerate(external_links["inputs"]):
            base_node_tree.links.new(
                link.from_node.outputs[link.from_socket.name],
                group_node.inputs[x]
                )

        for x, link in enumerate(external_links["outputs"]):
            base_node_tree.links.new(
                group_node.outputs[x],
                link.to_node.inputs[link.to_socket.name]
                )

        # Remove the original nodes from the base node tree since they've been copied into the group.
        for node in selected_nodes:
            base_node_tree.nodes.remove(node)

        return {'FINISHED'}


class BGToggleEditGroupOperator(Operator):
    """Create a node group from the selected nodes"""
    bl_idname = "bg.toggle_edit_group"
    bl_label = "Toggle BG Group"

    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        if hasattr(space_data, "node_tree"):
            if (space_data.node_tree):
                return space_data.tree_type == "BGTree"
        return False

    def execute(self, context):
        path = context.space_data.path
        active_node = path[-1].node_tree.nodes.active

        if hasattr(active_node, "node_tree") and active_node.select:
            path.append(active_node.node_tree, node=active_node)
            return {'FINISHED'}
        elif len(path) > 1:
            path.pop()

        return {'CANCELLED'}


def node_menu_addition(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("bg.group_nodes")
    layout.operator("bg.toggle_edit_group")



classes = [
    BGNodeGroup,
    BGGroupNodesOperator,
    BGToggleEditGroupOperator
    ]

addon_keymaps = []

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps.new(name="Node Generic", space_type='NODE_EDITOR')

    kmi = km.keymap_items.new("bg.group_nodes", 'G', 'PRESS', ctrl=True)
    addon_keymaps.append((km, kmi))

    kmi = km.keymap_items.new("bg.toggle_edit_group", 'TAB', 'PRESS')
    addon_keymaps.append((km, kmi))



    bpy.types.NODE_MT_node.append(node_menu_addition)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.types.NODE_MT_node.remove(node_menu_addition)
