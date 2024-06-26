from io_hubs_addon.components.components_registry import register_component, unregister_component, __components_registry
from io_scene_gltf2.io.com.gltf2_io_constants import TextureFilter, TextureWrap
from io_scene_gltf2.io.com import gltf2_io
from io_hubs_addon.io.utils import gather_property, gather_image, gather_vec_property, gather_color_property
from io_hubs_addon.components.utils import has_component
from bpy.types import NodeSocket
import bpy


def redraw_area(context, area_id):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == area_id:
                area.tag_redraw()
                context.window_manager.update_tag()


def gather_material_property(export_settings, blender_object, target, property_name):
    blender_material = getattr(target, property_name)
    if blender_material:
        if bpy.app.version < (4, 0, 0):
            material = gltf2_blender_gather_materials.gather_material(
                blender_material, 0, export_settings)
        else:
            material = gltf2_blender_gather_materials.gather_material(
                blender_material, export_settings)[0]
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


if bpy.app.version >= (3, 6, 0):
    from io_scene_gltf2.blender.exp.material import gltf2_blender_gather_materials
else:
    from io_scene_gltf2.blender.exp import gltf2_blender_gather_materials


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


def gather_object_property(export_settings, blender_object):
    if blender_object:
        if bpy.app.version < (3, 2, 0):
            node = gltf2_blender_gather_nodes.gather_node(
                blender_object,
                blender_object.library.name if blender_object.library else None,
                blender_object.users_scene[0],
                None,
                export_settings
            )
        else:
            vtree = export_settings['vtree']
            vnode = vtree.nodes[next((uuid for uuid in vtree.nodes if (
                vtree.nodes[uuid].blender_object == blender_object)), None)]
            node = vnode.node or gltf2_blender_gather_nodes.gather_node(
                vnode,
                export_settings
            )

        return {
            "__mhc_link_type": "node",
            "index": node
        }
    else:
        return None


def add_component_to_node(gltf2_object, dep, value, export_settings):
    try:
        from io_hubs_addon.io.utils import HUBS_CONFIG
    except ImportError:
        # A version of the io_hubs_addon below 1.5 is being used
        from io_hubs_addon.io.gltf_exporter import hubs_config as HUBS_CONFIG

    hubs_ext_name = HUBS_CONFIG["gltfExtensionName"]
    if type(gltf2_object) is tuple:
        extensions = gltf2_object[0].extensions
    else:
        extensions = gltf2_object.extensions

    if extensions is None:
        extensions = {}

    if hubs_ext_name not in extensions:
        extensions[hubs_ext_name] = {dep.get_name(): value}
        if type(gltf2_object) is tuple:
            gltf2_object[0].extensions = extensions
        else:
            gltf2_object.extensions = extensions
    else:
        if hasattr(extensions[hubs_ext_name], "extension"):
            if not dep.get_name() in extensions[hubs_ext_name].extension:
                extensions[hubs_ext_name].extension.update({dep.get_name(): value})
            else:
                extensions[hubs_ext_name].extension[dep.get_name()].update(value)
        else:
            if not dep.get_name() in extensions[hubs_ext_name]:
                extensions[hubs_ext_name].update({dep.get_name(): value})
            else:
                extensions[hubs_ext_name][dep.get_name()].update(value)


def update_gltf_network_dependencies(node, export_settings, blender_object, dep, value={"networked": "true"}):
    if type(blender_object) is bpy.types.Object:
        vtree = export_settings['vtree']
        vnode = vtree.nodes[next((uuid for uuid in vtree.nodes if (
            vtree.nodes[uuid].blender_object == blender_object)), None)]
        gltf_object = vnode.node or gltf2_blender_gather_nodes.gather_node(
            vnode,
            export_settings
        )
        add_component_to_node(gltf_object, dep, value, export_settings)
    elif type(blender_object) is bpy.types.Material:
        if bpy.app.version < (4, 0, 0):
            gltf_object = gltf2_blender_gather_materials.gather_material(
                blender_object, 0, export_settings)
        else:
            gltf_object = gltf2_blender_gather_materials.gather_material(
                blender_object,  export_settings)[0]
        add_component_to_node(gltf_object, dep, value, export_settings)


def get_input_entity(node, context, ob=None):
    target = None
    entity_socket = node.inputs.get("entity")
    if entity_socket:
        target = entity_socket.target
        if node.inputs.get("entity").is_linked and len(entity_socket.links) > 0:
            link = entity_socket.links[0]
            from_node = link.from_socket.node
            # This case should go away when we remove BGNode_variable_get
            if from_node.bl_idname == "BGNode_variable_get":
                from_target = get_input_entity(from_node, context, ob)
                # When copying entities the variable is updated in the variables list
                # but not on the socket so we pull the variable value directly from the list
                target = from_target.bg_global_variables.get(from_node.variableName).defaultEntity
            elif from_node.bl_idname == "BGNode_networkedVariable_get":
                from_target = get_input_entity(from_node, context, ob)
                # When copying entities the variable is updated in the variables list
                # but not on the socket so we pull the variable value directly from the list
                target = from_target.bg_global_variables.get(from_node.prop_name).defaultEntity
            elif from_node.bl_idname == "BGNode_hubs_entity_properties":
                from_target = get_input_entity(from_node, context, ob)
                target = from_target
            else:
                target = link.from_socket.target
        else:
            if entity_socket.entity_type == '':
                target = None
            elif entity_socket.entity_type in ["object", "self"]:
                target = ob if ob else context.active_object
            elif entity_socket.entity_type == "scene":
                target = context.scene
            elif entity_socket.entity_type == "graph":
                # When exporting we use the current exporting object as the target object
                if ob:
                    if type(ob) is bpy.types.Object:
                        target = context.active_object.bg_active_graph
                    else:
                        target = context.scene.bg_active_graph
                else:
                    if context.scene.bg_node_type == 'OBJECT':
                        target = context.active_object.bg_active_graph
                    else:
                        target = context.scene.bg_active_graph

    return target


def gather_socket_value(ob, export_settings, socket):
    if hasattr(socket, "bl_socket_idname"):
        socket_idname = socket.bl_socket_idname
    else:
        socket_idname = socket.bl_idname

    socket_type = socket_to_type[socket_idname]

    if socket_idname == "BGEnumSocket":
        return socket.default_value
    if socket_idname == "BGCustomEventSocket":
        return socket.name
    if socket_type == "entity":
        if socket.entity_type == "self":
            return gather_object_property(export_settings, ob)
        else:
            return gather_property(export_settings, socket, socket, "target")
    elif socket_type == "material":
        return gather_material_property(export_settings, socket, socket, "default_value")
    elif socket_type == "texture":
        if socket.is_linked:
            raise Exception("Linked textures not yet supported")
        else:
            return gather_texture_property(export_settings, socket, socket, "default_value")
    elif socket_type == "color":
        return gather_color_property(export_settings, socket, socket, "default_value", "COLOR_GAMMA")
    elif socket_type == "vec3":
        value = gather_vec_property(export_settings, socket, socket, "default_value")
        if export_settings['gltf_yup']:
            copy = value.copy()
            value["y"] = copy["z"]
            value["z"] = copy["y"]
        return value
    elif hasattr(socket, "default_value"):
        return gather_property(export_settings, socket, socket, "default_value")
    else:
        return None


def gather_deep_socket_value(socket, ob, export_settings, context):
    if socket.is_linked and len(socket.links) > 0:
        link = socket.links[0]
        from_node = link.from_socket.node
        # This case should go away when we remove BGNode_variable_get
        if from_node.bl_idname == "BGNode_variable_get":
            entity = get_input_entity(from_node, context, ob)
            # When copying entities the variable is updated in the variables list
            # but not on the socket so we pull the variable value directly from the list
            var = entity.bg_global_variables.get(from_node.prop_name)
            return gather_variable_value(ob, var, export_settings)
        elif from_node.bl_idname == "BGNode_networkedVariable_get":
            entity = get_input_entity(from_node, context, ob)
            # When copying entities the variable is updated in the variables list
            # but not on the socket so we pull the variable value directly from the list
            var = entity.bg_global_variables.get(from_node.prop_name)
            return gather_variable_value(ob, var, export_settings)
        else:
            return gather_socket_value(ob, export_settings, link.from_socket)
    else:
        return gather_socket_value(ob, export_settings, socket)


def gather_variable_value(ob, var, export_settings):
    value = None
    if var.type == "integer":
        value = var.defaultInt
    elif var.type == "boolean":
        value = var.defaultBoolean
    elif var.type == "float":
        value = var.defaultFloat
    elif var.type == "string":
        value = var.defaultString
    elif var.type == "vec3":
        value = gather_vec_property(export_settings, var, var, "defaultVec3")
        if export_settings['gltf_yup']:
            copy = value.copy()
            value["y"] = copy["z"]
            value["z"] = copy["y"]
    elif var.type == "animationAction":
        value = var.defaultAnimationAction
    elif var.type == "color":
        value = gather_color_property(export_settings, var, var, "defaultColor", "COLOR_GAMMA")
    elif var.type == "entity":
        if var.defaultEntity:
            if var.defaultEntity.name in bpy.context.view_layer.objects:
                value = gather_property(export_settings, var, var, "defaultEntity")
            else:
                raise Exception(
                    f"Variable {ob.name}/{var.name} entity {var.defaultEntity.name} does not exist in the scene")
    elif var.type == "material":
        if var.defaultMaterial:
            if var.defaultMaterial.name in bpy.data.materials:
                value = gather_material_property(export_settings, var, var, "defaultMaterial")
            else:
                raise Exception(
                    f"Variable {ob.name}/{var.name} material {var.defaultMaterial.name} does not exist in the scene")

    return value


def resolve_input_link(input_socket: bpy.types.NodeSocket) -> bpy.types.NodeLink:
    while isinstance(input_socket.links[0].from_node, bpy.types.NodeReroute):
        input_socket = input_socket.links[0].from_node.inputs[0]
    return input_socket.links[0]


def resolve_output_link(output_socket: bpy.types.NodeSocket) -> bpy.types.NodeLink:
    while isinstance(output_socket.links[0].to_node, bpy.types.NodeReroute):
        output_socket = output_socket.links[0].to_node.outputs[0]
    return output_socket.links[0]


def filter_on_components(self, ob):
    if hasattr(self, "poll_components") and self.poll_components:
        result = False
        components = self.poll_components.split(",")
        for component in components:
            result = result or has_component(ob, component)
        return result
    return True


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
    "enum": "BGEnumSocket"
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
    "BGHubsPlayerSocket": "player",
    "BGCustomEventSocket": "string"
}

prop_to_type = {
    "FloatProperty": "float",
    "IntProperty": "integer",
    "BoolProperty": "boolean",
    "PointerProperty": "entity",
    "StringProperty": "string",
    "FloatVectorProperty": "vec3",
    "EnumProperty": "enum"
}


def createSocketForComponentProperty(target, component, property_name):
    property_definition = component.bl_rna.properties[property_name]
    prop_type = property_definition.bl_rna.identifier
    prop_subtype = property_definition.subtype
    isArray = getattr(property_definition, 'is_array', None)
    if isArray and property_definition.is_array:
        if prop_subtype.startswith('COLOR'):
            socket_type = "color"
        elif prop_type == "BoolProperty":
            socket_type = "integer"
        else:
            socket_type = "vec3"
    elif prop_type in prop_to_type:
        socket_type = prop_to_type[prop_type]

    if socket_type:
        prop_value = getattr(component, property_name)
        if socket_type == "enum":
            target.new(type_to_socket[socket_type], "string")
            socket = target.get("string")
            for item in property_definition.enum_items:
                choice = socket.choices.add()
                choice.text = item.name
                choice.value = item.identifier
        else:
            target.new(type_to_socket[socket_type], socket_type)
            socket = target.get(socket_type)
            if socket_type == "integer" and isArray:
                value = 0
                for i in range(0, len(prop_value)):
                    if prop_value[i]:
                        value |= 1 << i
                socket.default_value = value
            else:
                socket.default_value = prop_value

    return socket


# This function is used by several node entity_type properties and
# it returns different values based on the node type (custom_type) and the
# object that it's attached to. We decide what type of object it's attached to by
# checking context.scene.bg_node_type but when exporting we can't trust
# context.scene.bg_node_type as that will point to the currently selected graph node type
# not to the actual object that's being exported.
# To workaround that we use context.scene.bg_export_type that will be set to
# the object type that is currently being exported.
# Quite a hack for so far I didn't find a better workaround.

def filter_entity_type(target, context):
    if not hasattr(target, "node_type"):
        target = target.node
    is_var_event_node = target.bl_idname in ["BGNode_variable_get",
                                             "BGNode_variable_set",
                                             "BGNode_customEvent_trigger",
                                             "BGNode_customEvent_onTriggered", "BGNode_networkedVariable_get",
                                             "BGNode_networkedVariable_set"]

    # Used for custom variables and events entity sockets
    if is_var_event_node:
        types = [("scene", "Scene", "Scene"),
                 ("graph", "Graph", "Graph"),
                 ("other", "Other", "Other")]

        # If bg_export_type is not None, it's export time
        if context.scene.bg_export_type != "none":
            if context.scene.bg_export_type != "scene":
                types.insert(0, ("object", "Self", "Self"))

        #  Execution time, bg_node_type will be set to the type of the current object
        elif context.scene.bg_node_type != 'SCENE':
            types.insert(0, ("object", "Self", "Self"))

    # Used for general nodes that have an entity socket
    else:
        types = [("other", "Other", "Other")]

        # If bg_export_type is not None, it's export time
        if context.scene.bg_export_type != "none":
            if context.scene.bg_export_type != "scene":
                types.insert(0, ("self", "Self", "Self"))

        #  Execution time, bg_node_type will be set to the type of the current object
        elif context.scene.bg_node_type != 'SCENE':
            types.insert(0, ("self", "Self", "Self"))

    return types


def should_export_node_entity(node, ob):
    if node.bl_idname in ["BGNode_networkedVariable_get", "BGNode_networkedVariable_set"]:
        target = get_input_entity(node, bpy.context, ob)
        if not target:
            raise Exception("Entity not set")
        if not object_exists(target):
            raise Exception(f"Entity {target.name} does not exist")
        has_prop = node.prop_name in target.bg_global_variables
        if not has_prop:
            raise Exception(f"Property {node.prop_name} does not exist")
        prop = target.bg_global_variables.get(node.prop_name)
        return prop.networked
    elif node.bl_idname in ["BGNode_variable_get", "BGNode_variable_set", "BGNode_customEvent_trigger", "BGNode_customEvent_onTriggered"]:
        return False
    else:
        return True


def update_nodes(self, context):
    if context.scene.bg_node_type == 'OBJECT':
        if hasattr(context.active_object, "bg_active_graph") and context.active_object.bg_active_graph is not None:
            for node in context.active_object.bg_active_graph.nodes:
                if hasattr(node, "refresh") and callable(getattr(node, "refresh")):
                    node.refresh()
    else:
        if hasattr(context.scene, "bg_active_graph") and context.scene.bg_active_graph is not None:
            for node in context.scene.bg_active_graph.nodes:
                if hasattr(node, "refresh") and callable(getattr(node, "refresh")):
                    node.refresh()


def update_graphs(self, context):
    if hasattr(context.active_object, "bg_active_graph") and context.active_object.bg_active_graph is not None:
        context.active_object.bg_active_graph.update()
    if hasattr(context.scene, "bg_active_graph") and context.scene.bg_active_graph is not None:
        context.scene.bg_active_graph.update()


def get_graph_from_node(node):
    return node.id_data


def object_exists(ob):
    from .behavior_graph import BGTree
    if type(ob) is bpy.types.Scene:
        return ob.name in bpy.data.scenes
    elif type(ob) is BGTree:
        return ob.name in bpy.data.node_groups
    elif type(ob) is bpy.types.Object:
        return ob.name in bpy.context.view_layer.objects
    return False


def unique_property_name(property, unique_name, name, value):
    import re

    def collection_from_element(self):
        import re
        # this gets the collection that the element is in
        path = self.path_from_id()
        match = re.match('(.*)\[\d*\]', path)
        parent = self.id_data
        try:
            coll_path = match.group(1)
        except AttributeError:
            raise TypeError("Property not element in a collection.")
        else:
            return parent.path_resolve(coll_path)

    def new_val(stem, nbr):
        # simply for formatting
        return '{st}.{nbr:03d}'.format(st=stem, nbr=nbr)

    # =====================================================

    if name not in unique_name:
        # don't want to handle
        property[name] = value
        return
    if value == getattr(property, name):
        # check for assignement of current value
        return

    coll = collection_from_element(property)
    if value not in coll:
        # if value is not in the collection, just assign
        property[name] = value
        return

    # see if value is already in a format like 'name.012'
    match = re.match('(.*)\.(\d{3,})', value)
    if match is None:
        stem, nbr = value, 1
    else:
        stem, nbr = match.groups()

    # check for each value if in collection
    new_value = new_val(stem, nbr)
    while new_value in coll:
        nbr += 1
        new_value = new_val(stem, nbr)
    property[name] = new_value


def get_variable_value(var):
    value = None
    if var.type == "integer":
        value = var.defaultInt
    elif var.type == "boolean":
        value = var.defaultBoolean
    elif var.type == "float":
        value = var.defaultFloat
    elif var.type == "string":
        value = var.defaultString
    elif var.type == "vec3":
        value = var.defaultVec3
    elif var.type == "animationAction":
        value = var.defaultAnimationAction
    elif var.type == "color":
        value = var.defaultColor
    elif var.type == "entity":
        value = var.defaultEntity
    elif var.type == "material":
        var.defaultMaterial

    return value


def get_prefs():
    return bpy.context.preferences.addons[__package__].preferences


def do_register(ComponentClass):
    register_component(ComponentClass)
    __components_registry[ComponentClass.get_name()] = ComponentClass


def do_unregister(ComponentClass):
    if ComponentClass.is_registered:
        unregister_component(ComponentClass)
        __components_registry.pop(ComponentClass.get_name())
