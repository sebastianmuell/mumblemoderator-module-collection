#!/usr/bin/env python
# -*- coding: utf-8
#
# Copyright (C) 2016 – 2017 Natenom <natenom@googlemail.com>
# Copyright (C) 2013 Stefan Hacker <dd0t@users.sourceforge.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Mumble Developers nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# `AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# lowbw.py
#

from mumo_module import (commaSeperatedIntegers,
                         MumoModule)
from threading import Timer
import re

class lowbw(MumoModule):
    default_config = {'lowbw':(
                                ('servers', commaSeperatedIntegers, []),
                                ('tidyupinterval', int, 300),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(
                                ('lowbwchannelname', str, 'autocreated'),
                                ('lowbwchanneldescription', str 'Description of low bandwidth channel'),
                                ('botgroup', str, 'bots'),
                                ('ignorechannels', commaSeperatedIntegers, [0]),
                                ('lowbwmessage', str, "<span style='color:red;'>A low bandwidth channel was automatically created by the server because a bot entered this channel. If you want to save bandwidth or do not want to hear the bot at all consider to enter this new channel :)</style>")
                                )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        self.watchdog = None

    def isBot(self, server, userid):
        '''Checks if userid is member of the bot group in the root channel'''
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        except AttributeError:
            scfg = self.cfg().all

        ACL = server.getACL(0)

        for group in ACL[1]:
            if (group.name == scfg.botgroup):
                if (userid in group.members):
                    return True

        return False

    def connected(self):
        #try:
        #    scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        #except AttributeError:
        #    scfg = self.cfg().all

        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        cfg = self.cfg()
        servers = cfg.lowbw.servers
        if not servers:
            servers = manager.SERVERS_ALL


        #servers = self.cfg().lowbw.servers
        #if not servers:
        #    servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

        # Code from https://github.com/mumble-voip/mumo/blob/master/modules/idlemove.py#L84
        if not self.watchdog:
            self.watchdog = Timer(cfg.lowbw.tidyupinterval, self.tidyup)
            self.watchdog.start()

    def disconnected(self): pass

    #
    #--- Server callback functions
    #
    def userTextMessage(self, server, user, message, current=None): pass
    def userConnected(self, server, state, context = None): pass
    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None):
        '''Handling for creating/removing low bw channels'''
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        if not self.isBot(server, state.userid):
            #self.log().debug("Ignoring Non-Bot %s in channel %s" % (state.name, state.channel))
            return

        if state.channel in scfg.ignorechannels:
            #self.log().debug("Ignoring bot %s in ignorechannels (channel id: %s)." % (state.name, state.channel))
            return

        linkedLowbwExists = False
        unlinkedLowbwExists = False
        channelstate = server.getChannelState(state.channel)

        # Ignore if current channel is a low bw one
        if channelstate.name == scfg.lowbwchannelname:
            self.log().debug("Bot(name: %s, id: %s) - Great, we are currently sitting in a lowbwchannel (name: %s, id: %s)." % (state.name, state.channel, channelstate.name, state.channel))
            return

        # Handle bot...
        #self.log().debug("Handling bot %s in channel %s" % (state.name, state.channel))

        # Check whether there is already a "low bw" channel by checking names from channel property "links".
        for link in channelstate.links:
            current_channel = server.getChannelState(link)
            if current_channel.name == scfg.lowbwchannelname:
                linkedLowbwExists = True
                break

        # For now until linking works check all subchannels in order to not create a mass of "lowbw" channels :P
        allchans = server.getChannels()

        for cid, cprops in allchans.iteritems():
            if cprops.parent == state.channel and cprops.name == scfg.lowbwchannelname:
                unlinkedLowbwExists = True
                break

        if unlinkedLowbwExists:
            self.log().debug("Bot(name: %s, id: %s) - Great, there exists an UNLINKED lowbwchannel (name: %s, id: %s) in current channel (id: %s)." % (state.name, state.channel, cprops.name, cprops.id, state.channel))
            return

        if linkedLowbwExists:
            self.log().debug("Bot(name: %s, id: %s) - Great, there exists a LINKED lowbwchannel (name: %s, id: %s) in current channel (id: %s)." % (state.name, state.channel, current_channel.name, current_channel.id, state.channel))
            return

        #self.log().debug("Bot(name: %s, id: %s) - There is NO low bw channel named \'%s\' linked to channelid \'%s\'" % (state.name, state.channel, scfg.lowbwchannelname, state.channel))

        # Create a low bw channel
        newLowbwChannelID = server.addChannel(scfg.lowbwchannelname, state.channel)
        self.log().info("Lowbw channel (name: %s, id: %s) created as a subchannel of %s" % (scfg.lowbwchannelname, newLowbwChannelID, state.channel))

        # Link newly created lowbwchannel.
        channelstate.links.append(newLowbwChannelID)
        channelstate.description = scfg.lowbwchanneldescription
        server.setChannelState(channelstate)
        server.sendMessageChannel(state.channel, False, scfg.lowbwmessage)
        self.log().info("Lowbw channel (name: %s, id: %s) linked with current channel (id: %s)." % (scfg.lowbwchannelname, newLowbwChannelID, state.channel))

        # Set ACL
        # acl = server.getACL(chanid) contains
        # out ACLList acls, out GroupList groups, out bool inherit
        # We need acl[0]

        #cacl = server.getACL(newLowbwChannelID)


        # Thanks for the code from hacst, see https://github.com/mumble-voip/mumo/blob/master/modules/source/source.py
        ACL = self.murmur.ACL
        S = self.murmur.PermissionSpeak # Speak

        server.setACL(newLowbwChannelID,
                          [ACL(applyHere = True, # Deny speak for botgroup in the lowbw channel.
                               applySubs = False,
                               userid = -1,
                               group = scfg.botgroup,
                               deny = S)],
                           [], True)
        # End of code from hacst, thanks much :)

    def tidyup(self):
        '''
            Iterate through all channels, find lowbwchannels and remove them if the following applies:
                * No bot is in the parent channel
                * No user is in the lowbwchannel
        '''

        # Code from https://github.com/mumble-voip/mumo/blob/master/modules/idlemove.py#L94 (except the iteration part)
        cfg = self.cfg()
        try:
            meta = self.manager().getMeta()

            if not cfg.lowbw.servers:
                servers = meta.getBootedServers()
            else:
                servers = [meta.getServer(server) for server in cfg.lowbw.servers]

            for server in servers:
                if not server: continue

                if server:
                    try:
                        scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
                    except AttributeError:
                        scfg = self.cfg().all

                    crowdedchannels = [] # List
                    allusers = server.getUsers()
                    for k, props in allusers.iteritems():
                        if props.channel not in crowdedchannels:
                            crowdedchannels.append(props.channel)

                    # Iterate through all channels and handle if it is a lowbwchannel
                    allchans = server.getChannels()
                    for cid, cprops in allchans.iteritems():
                        if cprops.name == scfg.lowbwchannelname: # It is a lowbwchannel
                            if (cid in crowdedchannels) or (cprops.parent in crowdedchannels):
                                self.log().debug("Channel \'%s\' (id: \'%s\') is a lowbwchannel and this channel OR its parent channel is crowded. Nothing to do." % (cprops.name, cid))
                                continue
                            else:
                                self.log().info("Channel \'%s\' (id: \'%s\') is a lowbwchannel and both this channel AND its parent channel are empty, removing it." % (cprops.name, cid))
                                server.removeChannel(cid)
        finally:
            # Renew the timer
            self.watchdog = Timer(cfg.lowbw.tidyupinterval, self.tidyup)
            self.watchdog.start()




    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
