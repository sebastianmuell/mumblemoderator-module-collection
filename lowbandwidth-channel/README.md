# mumo-lowbw
Creates a "Low Bandwidth" channel whenever a member of group "bots" enters a room. This channel is linked to the channel the bot sits in but the bot does not have permission to speak. This saves bandwidth for users with low bandwidth.

Technical background: If you local mute someone you still get his audio stream but it is discarded locally; it still needs bandwidth.

More background at https://blog.natenom.com/2015/12/acl-magic-for-your-mumble-server-let-users-decide-whether-to-listen-to-music-bots-or-not/.

## Documentation
* Documentation (English): https://wiki.natenom.de/en/mumble/tools/mumo/module/lowbw
* Documentation (German): https://wiki.natenom.de/mumble/tools/mumo/module/lowbw
