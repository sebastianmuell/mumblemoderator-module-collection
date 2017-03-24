#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2016 Natenom <natenom@googlemail.com>
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
# welcomemessage.py
# This modules displays an additional welcome message to users.
# One can declare if a welcome message is for registered users only, for unregistered
# for a specific group, etc.

from mumo_module import (commaSeperatedIntegers,
			 commaSeperatedBool,
                         MumoModule)
import re

class welcomemessage(MumoModule):
    default_config = {'welcomemessage':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(
                                ('welcomemessage_registered', str, ""),
                                ('welcomemessage_unregistered', str, "Hey, you are new to this server. You may create a temporary channel in '| Empfang / Public Lobby' -> '| Temporäre Räume / Temporary channels'.<br />If you want an own permanent channel please ask one of the administrators. See root channel description for a list of them."),
                                ('kick', commaSeperatedBool, [False])
                                )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().welcomemessage.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

    def isregistered(self, userid):
        if (userid == -1):
          return False
        else:
          return True

    def userConnected(self, server, user, context = None):
        log = self.log()
        #self.log().debug("User connected. OS: %s, Version: %s, Username: %s, Session ID: %s." % (state.os, state.version, state.name, state.session))

        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        except AttributeError:
            scfg = self.cfg().all

        if self.isregistered(user.userid): #User is registered
          if len(scfg.welcomemessage_registered) > 0:
            server.sendMessage(user.session, scfg.welcomemessage_registered)
        else:
          if len(scfg.welcomemessage_unregistered) > 0:
            server.sendMessage(user.session, scfg.welcomemessage_unregistered)

    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None): pass
    def userTextMessage(self, server, user, message, current=None): pass
    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
