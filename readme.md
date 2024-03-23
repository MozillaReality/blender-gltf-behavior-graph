# Installation and Basic Usage
Use the addon in conjunction with the [Mozilla Hubs Blender Exporter Addon](https://github.com/MozillaReality/hubs-blender-exporter).

Behavior graphs is still in alpha state and not part of the main Hubs client branch. That means it will not work on regular hubs instances or on the official hubs demo server. For testing, you can use the [public testing instance](https://testing.dev.myhubs.net/). This instance will be regularly updated with the development branch so you can expect it to have the latest code running anytime.

Alternatively, you can use [hubs-compose](https://github.com/mozilla/hubs-compose/) to run the whole stack locally. The current active branch before we merge in main is: https://github.com/mozilla/hubs/tree/behavior-graphs-spike-rebased
Users of the Hubs professional plan can upload a [custom client](https://hubs.mozilla.com/docs/setup-custom-client.html) using that branch.

Examples and demo scenes can be found in the repo [blender-behavior-graph-examples](https://github.com/MozillaReality/blender-behavior-graph-examples).

# Testing and Debugging
+ Use these url query parameters while testing: ?newLoader&ecsDebug&vr_entry_type=2d_now&entity_state_api
  + newLoader: Force use the new loader (required for BGs).
  + ecsDebug: Show the ECS debug panel. Good for debugging your entities while in the room.
  +  vr_entry_type: Skip the entry modal and go straight to the room. Good for saving time.
  +  entity_state_api: Enable pinning.
+ Use the &debugLocalScene query parameter while testing a local scene. Important: Make sure you are logged in the room otherwise it will just load the GLD as a media.
+ For testing networked scenes upload the scene to Spoke and change the room's scene.
+ File bugs in the hubs client repo adding the Behavior Graphs label so we can [track the open issues here](https://github.com/mozilla/hubs/labels/Behavior%20Graphs).
