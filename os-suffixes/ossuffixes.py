#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2010-2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2015 – 2017 Natenom <natenom@googlemail.com>
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

from mumo_module import (commaSeperatedIntegers,
                         MumoModule)
import re
from time import sleep

class ossuffixes(MumoModule):
    default_config = {'ossuffixes':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(
                                ('suffix_x11', str, " ☢"),
                                ('suffix_windows', str, " ❖"),
                                ('suffix_ios', str, " ☎"),
                                ('suffix_iphone', str, " ☎"),
                                ('suffix_mac', str, " ⌘"),
                                ('suffix_rubybot', str, " ♫"),
                                ('suffix_android', str, " ☎"),
                                ('excluded', str, 'exclude_notice'),
                                ('rename_registered_users_only', str, 'true')
                                )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()

    def isexcluded(self, server, userid):
        '''Checks if userid is member of the excluded group in the root channel'''
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        except AttributeError:
            scfg = self.cfg().all

        ACL = server.getACL(0)

        for group in ACL[1]:
            if (group.name == scfg.excluded):
                if (userid in group.members):
                    return True

        return False

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().ossuffixes.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

    def userConnected(self, server, state, context = None):
        sleep(2)
        state = server.getState(state.session) # Get state again after sleep to prevent from interrering with deaftoafk script, see https://github.com/Natenom/mumo-os-suffixes/issues/2; jupp, there are probably better solutions...

        log = self.log()
        #self.log().debug("User connected. OS: %s, Version: %s, Username: %s, Session ID: %s." % (state.os, state.version, state.name, state.session))

        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        except AttributeError:
            scfg = self.cfg().all

        if self.isexcluded(server, state.userid):
            return

        if scfg.rename_registered_users_only == "true" and state.userid == -1:
            # Ignore unregistered users.
            return

        suffix = ""

        if state.os.startswith("Android"):
            if not state.name.endswith(scfg.suffix_android):
                suffix = scfg.suffix_android
        elif state.os.startswith("iOS"):
            if not state.name.endswith(scfg.suffix_ios):
                suffix = scfg.suffix_ios
        elif state.os.startswith("iPhone"):
            if not state.name.endswith(scfg.suffix_iphone):
                suffix = scfg.suffix_iphone
        elif state.os.startswith("Mac"):
            if not state.name.endswith(scfg.suffix_mac):
                suffix = scfg.suffix_mac
        elif state.os.startswith("OSX"):
            if not state.name.endswith(scfg.suffix_mac):
                suffix = scfg.suffix_mac
        elif state.os.startswith("Win"):
            if not state.name.endswith(scfg.suffix_windows):
                suffix = scfg.suffix_windows
        elif state.os.startswith("X11"):
            if not state.name.endswith(scfg.suffix_x11):
                suffix = scfg.suffix_x11
        elif state.os.startswith("Linux"):
            if not state.name.endswith(scfg.suffix_rubybot):
                suffix = scfg.suffix_rubybot

        if len(suffix) > 0:
            state.name = state.name + " " + suffix
            try:
                server.setState(state)
            except self.murmur.InvalidSessionException:
                self.log().debug("User disconnected before I could change his status.")

    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None): pass
    def userTextMessage(self, server, user, message, current=None): pass
    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
