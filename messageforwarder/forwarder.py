#!/usr/bin/env python
# -*- coding: utf-8
#
# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2013 - 2017 Natenom <natenom@googlemail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:

# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Mumble Developers nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.

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
# forwarder.py
# Forwards messages to all linked channels.
#
from config import (commaSeperatedIntegers,
                         commaSeperatedBool)
from mumo_module import (MumoModule)
import re

class forwarder(MumoModule):
    default_config = {'forwarder':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(
                                ('forwarderprefix', str, 'Forwarded from channel \"{channel}\" from user \"{user}\":<br />{message}'),
                                ('forwardiforiginuserisoutsideoriginchannel', commaSeperatedBool, [True]),
                                ('messageforbotfilter', str, '^(\W[^\s.]+)(\s[^\s.]+)?$')
                                )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().forwarder.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #--- Server callback functions
    #

    def findLinks(self, channelid, server, LinkedChannels=None):
        '''Uses recursion to find all linked channels.
           Problem: A can be linked with B, but B can additionally be
           linked to C and D while D can be linked to E.
           In the end A,B,C,D and E are linked together but you need to read
           all channels in order to get everything thats linked...'''

        if LinkedChannels is None:
            LinkedChannels = []

        LinkedChannels.append(channelid)

        channel = server.getChannelState(channelid)
        for link in channel.links:
           if link not in LinkedChannels:
               LinkedChannels.extend(self.findLinks(link, server, LinkedChannels))

        return sorted(set(LinkedChannels))

    def userTextMessage(self, server, user, message, current=None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        if message.trees or message.sessions: #Ignore tree and private messages
            return

        regex_bot_message = re.compile(scfg.messageforbotfilter)
        # For users, who want to command a music bot. Example: .queue or .volume 60

        if scfg.messageforbotfilter and regex_bot_message.match(message.text):
            return

        originchannel = message.channels[0]
        originchannelstate = server.getChannelState(originchannel)
        links = self.findLinks(originchannel, server)

        if (scfg.forwardiforiginuserisoutsideoriginchannel == [False]) and (int(server.getState(user.session).channel) not in links):
            # Do not forward message for privacy reasons because a user from outside the channel cannot see whether it is linked or not.
            self.log().debug("Ignore message; user sits outside the linked channels and forwardiforiginuserisoutsideoriginchannel is set to %s." % scfg.forwardiforiginuserisoutsideoriginchannel)
            return

        if len(links) > 1:
            self.log().debug("LinkedChannels: %s" % (links))

        for link in links:
            if link != originchannel:
                self.log().debug("Forwardet to channel \"%s\" (%s)" % (server.getChannelState(link).name, link))
                server.sendMessageChannel(link, False, scfg.forwarderprefix.format(channel = originchannelstate.name, user = user.name, message = message.text))

    def userConnected(self, server, state, context = None): pass
    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None): pass
    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
