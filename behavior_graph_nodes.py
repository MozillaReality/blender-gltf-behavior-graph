import bpy
import os
from bpy.props import StringProperty, PointerProperty
from bpy.types import GeometryNode, Node, NodeTree, NodeSocket, NodeSocketStandard,NodeSocketInterface, ShaderNode, TextureNode, Operator, NodeGroupInput, NodeReroute, NodeSocketString, NodeSocketBool, NodeSocketFloat
from bpy.utils import register_class, unregister_class
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

from io_hubs_addon.io.utils import gather_property, gather_image
from io_hubs_addon.components.utils import has_component

auto_casts = {
    ("BGHubsEntitySocket", "NodeSocketString"): "BGNode_hubs_entity_toString",

    ("NodeSocketFloat", "NodeSocketString"): "BGNode_math_toString_float",
    ("NodeSocketBool", "NodeSocketString"): "BGNode_math_toString_boolean",
    ("NodeSocketInt", "NodeSocketString"): "BGNode_math_toString_integer",
    ("NodeSocketVectorXYZ", "NodeSocketString"): "BGNode_math_toString_vec3",

    ("NodeSocketString", "NodeSocketFloat"): "BGNode_math_toFloat_string",
    ("NodeSocketBool", "NodeSocketFloat"): "BGNode_math_toFloat_boolean",
    ("NodeSocketInt", "NodeSocketFloat"): "BGNode_math_toFloat_integer",

    ("NodeSocketFloat", "NodeSocketInt"): "BGNode_math_toInteger_float",
    ("NodeSocketString", "NodeSocketInt"): "BGNode_math_toInteger_string",
    ("NodeSocketBool", "NodeSocketInt"): "BGNode_math_toInteger_boolean",

    ("NodeSocketString", "NodeSocketBool"): "BGNode_math_toBoolean_string",
    ("NodeSocketInt", "NodeSocketBool"): "BGNode_math_toBoolean_integer",

    ("NodeSocketVectorXYZ", "NodeSocketVectorEuler"): "BGNode_math_vec3_toEuler",
    ("NodeSocketVectorEuler", "NodeSocketVectorXYZ"): "BGNode_math_euler_toVec3",

    ("NodeSocketVectorXYZ", "NodeSocketFloat"): "BGNode_math_toFloat_vec3",
    ("NodeSocketFloat", "NodeSocketVectorXYZ"): "BGNode_math_toVec3_float",
}

class BGTree(NodeTree):
    bl_idname = "BGTree"
    bl_label = "Behavior Graph"
    bl_icon = "NODETREE"

    # TODO HACK to stop log spam when editing group inputs
    type: StringProperty("BGTREE")

    def mark_invalid_links(self):
        print("mark invalid links")
        for link in self.links:
            if type(link.from_socket) != type(link.to_socket):
                link.is_valid = False

    def update(self):
        for link in self.links:
            if type(link.from_socket) != type(link.to_socket):
                cast_key = (link.from_socket.bl_idname, link.to_socket.bl_idname)
                # if link.from_socket.bl_idname.startswith("NodeSocketVector") and link.to_socket.bl_idname.startswith("NodeSocketVector"):
                #     continue
                if isinstance(link.from_socket.node, NodeReroute):
                    from_node = link.from_socket.node
                    from_node.outputs.clear()
                    from_node.outputs.new(link.to_socket.bl_idname, "Output")
                    self.links.new(from_node.outputs["Output"], link.to_socket)
                elif isinstance(link.to_socket.node, NodeReroute):
                    to_node = link.to_socket.node
                    to_node.inputs.clear()
                    to_node.inputs.new(link.from_socket.bl_idname, "Input")
                    self.links.new(link.from_socket, to_node.inputs["Input"])
                elif cast_key in auto_casts:
                    try:
                        node = self.nodes.new(auto_casts[cast_key])
                        node.location = [link.from_node.location[0] + abs(link.from_node.location[0] - link.to_node.location[0])/2, link.from_node.location[1]]
                        self.links.new(link.from_socket, node.inputs[0])
                        self.links.new(node.outputs[0], link.to_socket)
                        node.hide = len(node.inputs) <= 1 and len(node.outputs) <= 1
                        link.from_node.select = False
                        node.select = True
                    except:
                        self.links.remove(link)
                elif type(link.to_socket) == BGEnumSocket and type(link.from_socket) == NodeSocketString:
                    pass
                else:
                    self.links.remove(link)

class BGFlowSocket(NodeSocketStandard):
    bl_label = "Behavior Graph Flow"

    def __init__(self):
        self.display_shape = "DIAMOND"
        if self.is_output:
            self.link_limit = 1
        else: 
            self.link_limit = 0

    def draw(self, context, layout, node, text):
        if text == "flow":
            layout.label(text="▶")
        elif self.is_output:
            layout.label(text = text + " ▶")
        else:
            layout.label(text = "▶ " + text)

    def draw_color(self, context, node):
        return (1.0, 1.0, 1.0, 1.0)

class BGHubsEntitySocket(NodeSocketStandard):
    bl_label = "Hubs Entity"

    target: PointerProperty(
        name="Target",
        type=bpy.types.Object,
        # poll=filter_on_component
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "target", text=text)

    def draw_color(self, context, node):
        return (0.2, 1.0, 0.2, 1.0)


def get_choices(self, context):
    return [(choice.value, choice.text, "") for choice in self.choices]

class BGEnumSocketChoice(bpy.types.PropertyGroup):
    text: StringProperty()
    value: StringProperty()

class BGEnumSocket(NodeSocketStandard):
    bl_label = "String Choice"

    default_value: bpy.props.EnumProperty(
        name="",
        items=get_choices
    )

    choices: bpy.props.CollectionProperty(type=BGEnumSocketChoice)

    def draw(self, context, layout, node, text):
        if self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        return (0.4, 0.7, 1.0, 1.0)

class BGHubsAnimationActionSocketInterface(NodeSocketInterface):
    bl_idname = "BGHubsAnimationActionSocketInterface"
    bl_socket_idname = "BGHubsAnimationActionSocket"

    def draw(self, context, layout):
        pass

    def draw_color(self, context):
        return (0.2, 1.0, 1.0, 1.0)

class BGHubsAnimationActionSocket(NodeSocketStandard):
    bl_label = "Hubs AnimationAction"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (0.2, 1.0, 1.0, 1.0)

class BGHubsPlayerSocketInterface(NodeSocketInterface):
    bl_idname = "BGHubsPlayerSocketInterface"
    bl_socket_idname = "BGHubsPlayerSocket"

    def draw(self, context, layout):
        pass

    def draw_color(self, context):
        return (1.00, 0.91, 0.34, 1.0)

class BGHubsPlayerSocket(NodeSocketStandard):
    bl_label = "Hubs Player"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (1.00, 0.91, 0.34, 1.0)

class BGNode():
    bl_label = "Behavior Graph Node"
    bl_icon = "NODE"

    def init(self, context):
        self.use_custom_color = True

    @classmethod
    def poll(cls, ntree):
        # return True
        return ntree.bl_idname == 'BGTree'

class BGEventNode():
    def init(self, context):
        super().init(context)
        self.color = (0.6, 0.2, 0.2)
        self.outputs.new("BGFlowSocket", "flow")

class BGActionNode():
    def init(self, context):
        super().init(context)
        self.color = (0.2, 0.2, 0.6)
        self.inputs.new("BGFlowSocket", "flow")
        self.outputs.new("BGFlowSocket", "flow")

entity_property_settings = {
    "visible": ("NodeSocketBool", False),
    "position": ("NodeSocketVectorXYZ", [0.0,0.0,0.0]),
    "rotation": ("NodeSocketVectorEuler", [0.0,0.0,0.0]),
    "scale": ("NodeSocketVectorXYZ", [1.0,1.0,1.0]),
}

def update_target_property(self, context):
    if self.inputs and len(self.inputs) > 2:
        self.outputs.remove(self.inputs[2])
    setattr(self, "node_type",  "hubs/entity/set/" + self.targetProperty)
    (socket_type, default_value) = entity_property_settings[self.targetProperty]
    sock = self.inputs.new(socket_type, self.targetProperty)
    sock.default_value = default_value

class BGHubsSetEntityProperty(BGActionNode, BGNode, Node):
    bl_label = "Set Entity Property"

    node_type: bpy.props.StringProperty()

    targetProperty: bpy.props.EnumProperty(
        name="",
        items=[
            ("visible", "visible", ""),
            ("position", "position", ""),
            ("rotation", "rotation", ""),
            ("scale", "scale", "")
        ],
        default="visible",
        update=update_target_property
    )

    def init(self, context):
        super().init(context)
        self.color = (0.2, 0.6, 0.2)
        self.inputs.new("BGHubsEntitySocket", "entity")
        update_target_property(self, context)

    def draw_buttons(self, context, layout):
        layout.prop(self, "targetProperty")


class BGNode_hubs_onInteract(BGEventNode, BGNode, Node):
    bl_label = "On Interact"
    node_type = "hubs/onInteract"

    target: PointerProperty(
        name="Target",
        type=bpy.types.Object,
        # poll=filter_on_component
    )

    def init(self, context):
        super().init(context)
        self.outputs.new("BGHubsEntitySocket", "entity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target")

def has_collider(self, ob):
    return has_component(ob, "physics-shape")

class BGNode_hubs_onCollisionEnter(BGEventNode, BGNode, Node):
    bl_label = "On Collision Enter"
    node_type = "hubs/onCollisionEnter"

    target: PointerProperty(name="Target", type=bpy.types.Object, poll=has_collider)

    def init(self, context):
        super().init(context)
        self.outputs.new("BGHubsEntitySocket", "entity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target")

class BGNode_hubs_onCollisionStay(BGEventNode, BGNode, Node):
    bl_label = "On Collision Stay"
    node_type = "hubs/onCollisionStay"

    target: PointerProperty(name="Target", type=bpy.types.Object, poll=has_collider)

    def init(self, context):
        super().init(context)
        self.outputs.new("BGHubsEntitySocket", "entity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target")

class BGNode_hubs_onCollisionExit(BGEventNode, BGNode, Node):
    bl_label = "On Collision Exit"
    node_type = "hubs/onCollisionExit"

    target: PointerProperty(name="Target", type=bpy.types.Object, poll=has_collider)

    def init(self, context):
        super().init(context)
        self.outputs.new("BGHubsEntitySocket", "entity")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target")

class BGNode_hubs_onPlayerCollisionEnter(BGEventNode, BGNode, Node):
    bl_label = "On Player Collision Enter"
    node_type = "hubs/onPlayerCollisionEnter"

    target: PointerProperty(name="Target", type=bpy.types.Object, poll=has_collider)

    def init(self, context):
        super().init(context)
        self.outputs.new("BGHubsPlayerSocket", "player")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target")

class BGNode_hubs_onPlayerCollisionStay(BGEventNode, BGNode, Node):
    bl_label = "On Player Collision Stay"
    node_type = "hubs/onPlayerCollisionStay"

    target: PointerProperty(name="Target", type=bpy.types.Object, poll=has_collider)

    def init(self, context):
        super().init(context)
        self.outputs.new("BGHubsPlayerSocket", "player")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target")

class BGNode_hubs_onPlayerCollisionExit(BGEventNode, BGNode, Node):
    bl_label = "On Player Collision Exit"
    node_type = "hubs/onPlayerCollisionExit"

    target: PointerProperty(name="Target", type=bpy.types.Object, poll=has_collider)

    def init(self, context):
        super().init(context)
        self.outputs.new("BGHubsPlayerSocket", "player")

    def draw_buttons(self, context, layout):
        layout.prop(self, "target")


def update_output_sockets(self, context):
    existing_outputs = len(self.outputs)
    print("existing", existing_outputs, "desired", self.numOutputs)
    if(existing_outputs < self.numOutputs):
        for i in range(existing_outputs, self.numOutputs):
            self.outputs.new("BGFlowSocket", f"{i+1}")
    elif existing_outputs > self.numOutputs:
        for i in range(self.numOutputs, existing_outputs):
            self.outputs.remove(self.outputs[f"{i+1}"])

class BGNode_flow_sequence(BGNode, Node):
    bl_label = "Sequence"
    node_type = "flow/sequence"

    numOutputs: bpy.props.IntProperty(
        name="Outputs",
        default=2,
        min=1,
        update=update_output_sockets
    )

    def init(self, context):
        super().init(context)
        self.color = (0.2, 0.2, 0.2)
        self.inputs.new("BGFlowSocket", "flow")
        update_output_sockets(self, context)

    def draw_buttons(self, context, layout):
        layout.prop(self, "numOutputs")


def get_available_input_sockets(self, context):
    tree = self.id_data
    if tree is not None:
        return [(socket.name, socket.name, socket.name) for socket in tree.inputs]
    else:
        return []

def update_selected_variable_input(self, context):
    # Remove previous socket
    if self.inputs and len(self.inputs) > 1:
        self.inputs.remove(self.inputs[1])

    # Create a new socket based on the selected variable type
    tree = self.id_data
    if tree is not None:
        selected_socket = tree.inputs[self.variableId]
        socket_type = selected_socket.bl_socket_idname
        if socket_type == "NodeSocketVector":
            socket_type = "NodeSocketVectorXYZ"
        self.inputs.new(socket_type, "value")

    return None

def update_selected_variable_output(self, context):
    # Remove previous socket
    if self.outputs:
        self.outputs.remove(self.outputs[0])

    # Create a new socket based on the selected variable type
    tree = self.id_data
    if tree is not None:
        print(self.variableId)
        selected_socket = tree.inputs[self.variableId]
        socket_type = selected_socket.bl_socket_idname
        if socket_type == "NodeSocketVector":
            socket_type = "NodeSocketVectorXYZ"
        self.outputs.new(socket_type, "value")

    return None

class BGNode_variable_get(BGNode, Node):
    bl_label = "Get Variable"
    node_type = "variable/get"

    variableId: bpy.props.EnumProperty(
        name="Variable",
        description="Variable",
        items=get_available_input_sockets,
        update=update_selected_variable_output,
    )

    def init(self, context):
        super().init(context)
        self.color = (0.2, 0.6, 0.2)
        update_selected_variable_output(self, context)

    def draw_buttons(self, context, layout):
        layout.prop(self, "variableId")


class BGNode_variable_set(BGActionNode, BGNode, Node):
    bl_label = "Set Variable"
    node_type = "variable/set"

    variableId: bpy.props.EnumProperty(
        name="Value",
        description="Variable Value",
        items=get_available_input_sockets,
        update=update_selected_variable_input
    )

    def init(self, context):
        super().init(context)
        self.color = (0.2, 0.6, 0.2)
        update_selected_variable_input(self, context)

    def draw_buttons(self, context, layout):
        layout.prop(self, "variableId")

class BGCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        # return True
        return context.space_data.tree_type == "BGTree"

behavior_graph_node_categories = {
    "Event": [
        NodeItem("BGNode_hubs_onInteract"),
        NodeItem("BGNode_hubs_onCollisionEnter"),
        NodeItem("BGNode_hubs_onCollisionStay"),
        NodeItem("BGNode_hubs_onCollisionExit"),
        NodeItem("BGNode_hubs_onPlayerCollisionEnter"),
        NodeItem("BGNode_hubs_onPlayerCollisionStay"),
        NodeItem("BGNode_hubs_onPlayerCollisionExit"),
    ],
   "Entity": [
        NodeItem("BGHubsSetEntityProperty"),
    ],
    "Variables": [
        NodeItem("BGNode_variable_get"),
        NodeItem("BGNode_variable_set"),
    ],
   "Flow": [
        NodeItem("BGNode_flow_sequence"),
    ],
}

all_classes = [
    BGTree,
    BGFlowSocket,
    BGHubsEntitySocket,
    BGHubsAnimationActionSocket,
    BGHubsAnimationActionSocketInterface,
    BGHubsPlayerSocket,
    BGHubsPlayerSocketInterface,

    BGEnumSocketChoice,
    BGEnumSocket,

    BGNode_variable_get,
    BGNode_variable_set,
    BGNode_flow_sequence,

    BGNode_hubs_onInteract,
    BGNode_hubs_onCollisionEnter,
    BGNode_hubs_onCollisionStay,
    BGNode_hubs_onCollisionExit,
    BGNode_hubs_onPlayerCollisionEnter,
    BGNode_hubs_onPlayerCollisionStay,
    BGNode_hubs_onPlayerCollisionExit,

    BGHubsSetEntityProperty,
]

hardcoded_nodes = {node.node_type for node in all_classes if hasattr(node,"node_type") }

type_to_socket = {
    "float": "NodeSocketFloat",
    "integer": "NodeSocketInt",
    "boolean": "NodeSocketBool",
    "entity": "BGHubsEntitySocket",
    "flow": "BGFlowSocket",
    "string": "NodeSocketString",
    "vec3": "NodeSocketVectorXYZ",
    "euler": "NodeSocketVectorEuler",
    "animationAction": "BGHubsAnimationActionSocket",
    "player": "BGHubsPlayerSocket",
    "material": "NodeSocketMaterial",
    "texture": "NodeSocketTexture",
    "color": "NodeSocketColor",
}

socket_to_type = {
    "NodeSocketFloat": "float",
    "NodeSocketInt": "integer",
    "NodeSocketBool": "boolean",
    "BGHubsEntitySocket": "entity",
    "BGFlowSocket": "flow",
    "NodeSocketString": "string",
    "NodeSocketVector": "vec3",
    "NodeSocketVectorXYZ": "vec3",
    "NodeSocketMaterial": "material",
    "NodeSocketTexture": "texture",
    "NodeSocketColor": "color",
    "NodeSocketVectorEuler": "euler",
    "BGHubsAnimationActionSocket": "animationAction",
    "BGEnumSocket": "string",
    "BGHubsPlayerSocket": "player"
}

category_colors = {
    "Event":  (0.6, 0.2, 0.2),
    "Flow":  (0.2, 0.2, 0.2),
    "Time":  (0.3, 0.3, 0.3),
    "Action":  (0.2, 0.2, 0.6),
    "None": (0.6, 0.6, 0.2)
}

def create_node_class(node_data):
    label = node_data["type"]
    if "label" in node_data:
        # label = "%s (%s)" % (node_data["label"], node_data["type"])
        label = node_data["label"]

    class CustomNode(BGNode, Node):
        bl_label = label

        node_type = node_data["type"]

        def init(self, context):
            super().init(context)

            if node_data["category"] in category_colors:
                self.color = category_colors[node_data["category"]]
            else:
                self.color = category_colors["None"]

            for input_data in node_data["inputs"]:

                if "choices" in input_data:
                    sock = self.inputs.new("BGEnumSocket", input_data["name"])
                    for choice_data in input_data["choices"]:
                        choice = sock.choices.add()
                        choice.text = choice_data["text"]
                        choice.value = choice_data["value"]
                else:
                    socket_type = type_to_socket[input_data["valueType"]]
                    sock = self.inputs.new(socket_type, input_data["name"])

                if "defaultValue" in input_data:
                    if (input_data["valueType"] == 'vec3' or input_data["valueType"] == "euler"):
                        sock.default_value[0] = input_data["defaultValue"]["x"]
                        sock.default_value[1] = input_data["defaultValue"]["y"]
                        sock.default_value[2] = input_data["defaultValue"]["z"]
                    else:
                        sock.default_value = input_data["defaultValue"]
                if "description" in input_data:
                    sock.description = input_data["description"]

            for output_data in node_data["outputs"]:
                socket_type = type_to_socket[output_data["valueType"]]
                sock = self.outputs.new(socket_type, output_data["name"])
                if (output_data["valueType"] != 'vec3' and output_data["valueType"] != "euler") and "defaultValue" in output_data:
                    sock.default_value = output_data["defaultValue"]
                if "description" in output_data:
                    sock.description = output_data["description"]

    CustomNode.__name__ = "BGNode_" + node_data['type'].replace("/", "_")
    print(CustomNode.__name__)

    return CustomNode

import json
def read_nodespec(filename):
    with open(filename, "r") as file:
        nodes = json.load(file)
        for node_spec in nodes:
            if node_spec["type"] in hardcoded_nodes:
                print("SKIP", node_spec["type"])
                continue
            category = node_spec["category"]
            if not category in behavior_graph_node_categories:
                behavior_graph_node_categories[category] = []
            node_class = create_node_class(node_spec)
            all_classes.append(node_class)
            behavior_graph_node_categories[category].append(NodeItem(node_class.__name__))
            # bpy.utils.register_class(node_class)
        # print(test_classes)
        #

def resolve_input_link(input_socket: bpy.types.NodeSocket) -> bpy.types.NodeLink:
    while isinstance(input_socket.links[0].from_node, bpy.types.NodeReroute):
        input_socket = input_socket.links[0].from_node.inputs[0]
    return input_socket.links[0]

def resolve_output_link(output_socket: bpy.types.NodeSocket) -> bpy.types.NodeLink:
    while isinstance(output_socket.links[0].to_node, bpy.types.NodeReroute):
        output_socket = output_socket.links[0].to_node.outputs[0]
    return output_socket.links[0]

from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials
from io_scene_gltf2.io.com import gltf2_io
from io_scene_gltf2.io.com.gltf2_io_constants import TextureFilter, TextureWrap

def gather_material_property(export_settings, blender_object, target, property_name):
    blender_material = getattr(target, property_name)
    if blender_material:
        material = gltf2_blender_gather_materials.gather_material(blender_material, -1, export_settings)
        return {
            "__mhc_link_type": "material",
            "index": material
        }
    else:
        return None

def __gather_mag_filter(blender_shader_node, export_settings):
    if blender_shader_node.use_interpolation:
        return TextureFilter.Linear
    return TextureFilter.Nearest

def __gather_min_filter(blender_shader_node, export_settings):
    if blender_shader_node.use_interpolation:
        if blender_shader_node.use_mipmap:
            return TextureFilter.LinearMipmapLinear
        else:
            return TextureFilter.Linear
    if blender_shader_node.use_mipmap:
        return TextureFilter.NearestMipmapNearest
    else:
        return TextureFilter.Nearest

def __gather_wrap(blender_shader_node, export_settings):
    # First gather from the Texture node
    if blender_shader_node.extension == 'EXTEND':
        wrap_s = TextureWrap.ClampToEdge
    elif blender_shader_node.extension == 'CLIP':
        # Not possible in glTF, but ClampToEdge is closest
        wrap_s = TextureWrap.ClampToEdge
    elif blender_shader_node.extension == 'MIRROR':
        wrap_s = TextureWrap.MirroredRepeat
    else:
        wrap_s = TextureWrap.Repeat
    wrap_t = wrap_s

    # Omit if both are repeat
    if (wrap_s, wrap_t) == (TextureWrap.Repeat, TextureWrap.Repeat):
        wrap_s, wrap_t = None, None

    return wrap_s, wrap_t


def gather_texture_property(export_settings, blender_object, target, property_name):
    blender_texture = getattr(target, property_name)

    wrap_s, wrap_t = __gather_wrap(blender_texture, export_settings)
    sampler = gltf2_io.Sampler(
        extensions=None,
        extras=None,
        mag_filter=__gather_mag_filter(blender_texture, export_settings),
        min_filter=__gather_min_filter(blender_texture, export_settings),
        name=None,
        wrap_s=wrap_s,
        wrap_t=wrap_t,
    )

    if blender_texture:
        texture = gltf2_io.Texture(
            extensions=None,
            extras=None,
            name=blender_texture.name,
            sampler=sampler,
            source=gather_image(blender_texture.image, export_settings)
        )
        return {
            "__mhc_link_type": "texture",
            "index": texture
        }
    else:
        return None

def get_socket_value(export_settings, socket : NodeSocket):
    if hasattr(socket, "bl_socket_idname"):
        socket_idname = socket.bl_socket_idname
    else:
        socket_idname = socket.bl_idname

    socket_type = socket_to_type[socket_idname]

    if socket_idname == "BGEnumSocket":
        return socket.default_value
    if socket_type == "entity":
        return gather_property(export_settings, socket, socket, "target")
    elif socket_type == "material":
        return gather_material_property(export_settings, socket, socket, "default_value")
    elif socket_type == "texture":
            return gather_texture_property(export_settings, socket, socket, "default_value")
    elif socket_type == "color":
        a = socket.default_value
        return [a[0], a[1], a[2]]
    elif socket_type == "vec3": # TODO gather_property seems to not handle this correctly
        a = socket.default_value
        return {"x": a[0], "y": a[1], "z": a[2]}
    elif hasattr(socket, "default_value"):
        return gather_property(export_settings, socket, socket, "default_value")
    else:
        return None

def extract_behavior_graph_data(node_tree, export_settings):
    data = {
        "variables": [],
        "nodes": []
    }

    for i, socket in enumerate(node_tree.inputs):
        socket_type = socket_to_type[socket.bl_socket_idname]
        value = get_socket_value(export_settings, socket)
        print(socket.name, socket_type, value)
        data["variables"].append({
            "name": socket.name,
            "id": i,
            "valueTypeName": socket_type,
            "initialValue": value
        })

    for node in node_tree.nodes:
        if not isinstance(node, BGNode):
            continue

        node_data = {
            "id": str(node.name),
            "type": node.node_type,
            "parameters": {},
            "configuration": {},
            "flows": {}
        }


        for output_socket in node.outputs:
            if isinstance(output_socket, BGFlowSocket) and output_socket.is_linked:
                link = resolve_output_link(output_socket)
                print(link)
                node_data["flows"][output_socket.identifier] = {
                    "nodeId": link.to_node.name,
                    "socket": link.to_socket.identifier
                }
        for input_socket in node.inputs:
            if isinstance(input_socket, BGFlowSocket):
                pass
            else:
                if input_socket.is_linked:
                    link = resolve_input_link(input_socket)
                    node_data["parameters"][input_socket.identifier] = {
                        "link": {
                            "nodeId": link.from_node.name,
                            "socket": link.from_socket.identifier
                        }
                    }
                elif isinstance(input_socket, BGHubsEntitySocket):
                    node_data["parameters"][input_socket.identifier] = { "value": gather_property(export_settings, input_socket, input_socket, "target") }
                else:
                    value = get_socket_value(export_settings, input_socket)
                    node_data["parameters"][input_socket.identifier] = { "value": value }

        if isinstance(node, BGNode_variable_get) or isinstance(node, BGNode_variable_set):
            print("VAR NODE", node.variableId, node_tree.inputs.find(node.variableId))
            node_data["configuration"]["variableId"] = node_tree.inputs.find(node.variableId)
        elif hasattr(node, "__annotations__"):
            for key in node.__annotations__.keys():
                node_data["configuration"][key] = gather_property(export_settings, node, node, key)

        data["nodes"].append(node_data)

    return data

# behavior_graph_data_list = []
# for node_group in bpy.data.node_groups:
#     if node_group.bl_idname == "BGTree":
#         behavior_graph_data = extract_behavior_graph_data(node_group)
#         behavior_graph_data_list.append(behavior_graph_data)
# pprint(behavior_graph_data_list)


class glTF2ExportUserExtension:
    def __init__(self):
        # We need to wait until we create the gltf2UserExtension to import the gltf2 modules
        # Otherwise, it may fail because the gltf2 may not be loaded yet
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension

        self.Extension = Extension

    def gather_gltf_extensions_hook(self, gltf2_object, export_settings):
        print("GATHERING BG")
        behaviors = [extract_behavior_graph_data(node_group, export_settings) for node_group in bpy.data.node_groups if node_group.bl_idname == "BGTree"]
        if behaviors:
            gltf2_object.extensions["MOZ_behavior"] = self.Extension(
                name="MOZ_behavior",
                extension={
                    "behaviors": behaviors
                },
                required=False
            )


def register():
    read_nodespec(os.path.join(os.path.dirname(os.path.abspath(__file__)), "nodespec.json"))

    for cls in all_classes:
        register_class(cls)

    print(behavior_graph_node_categories)
    categories = [BGCategory("BEHAVIOR_GRAPH_" + category.replace(" ", "_"), category, items=items) for category, items in behavior_graph_node_categories.items()]
    print(categories)
    register_node_categories("BEHAVIOR_GRAPH_NODES", categories)

def unregister():
    unregister_node_categories("BEHAVIOR_GRAPH_NODES")

    for cls in reversed(all_classes):
        unregister_class(cls)

if __name__ == "__main__":
    register()
