#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2010-2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2015-2016 Natenom <natenom@googlemail.com>
# Copyright (C) 2016 Nascher <kevin@nascher.org>
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

"""
wrongversion.py
This module notifies or notifies and kicks the user,
if the user connects with an outdated Mumble client to the server.
"""

from mumo_module import (commaSeperatedIntegers,
                         commaSeperatedBool,
                         MumoModule)
import re


class wrongversion(MumoModule):
    default_config = {'wrongversion': (
            ('servers', commaSeperatedIntegers, []),
        ),
        lambda x: re.match('(all)|(server_\d+)', x): (
            ('message', str, "<font style='color:red'>Hi %s, "
                             "you are using an old Mumble version. "
                             "Please consider an update "
                             "for a better user experience :)<br />See "
                             "<a href='https://wiki.mumble.info/wiki/'>"
                             "here</a> to get a list of recent versions "
                             "for your operating system.</font>"),
            ('kick', commaSeperatedBool, [False]),
            ('version_pc', str, "1.2.19"),
            ('version_android', str, "3.2.0"),
            ('version_ios', str, "1.3.0"),
            ('version_iphone', str, "1.3.0"),
            ('check_only_official_pc_packages', commaSeperatedBool, [True])
        )
    }

    def __init__(self, name, manager, configuration=None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().wrongversion.servers
        if not servers:
            servers = manager.SERVERS_ALL
        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    # --- Server callback functions
    #

    def convert_version_string(self, version):
        version_sub = version.split(".")
        version_bin = bin((((int(version_sub[0]) << 8)
                          + int(version_sub[1])) << 8)
                          + int(version_sub[2]))
        return int(version_bin, 2)

    def grab_release_version(self, release):
        find_version_regex = re.compile('\d+([.]\d+)+')
        version_str = find_version_regex.search(release).group(0)
        return version_str

    def userConnected(self, server, state, context=None):
        log = self.log()

        # Log level from debug = 10
        if log.getEffectiveLevel() == 10:
            if state.os.startswith("Android") or state.os.startswith("iOS"):
                version_state = self.grab_release_version(state.release)
                log.debug("User connected. OS: %s, "
                          "Version: %s, Username: %s, "
                          "Session ID: %s." % (state.os, version_state,
                                               state.name, state.session))
            else:
                log.debug("User connected. OS: %s, "
                          "Version: %s, Username: %s, "
                          "Session ID: %s." % (state.os, state.version,
                                               state.name, state.session))
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(server.id()))
        except AttributeError:
            scfg = self.cfg().all

        is_old = False
        if state.os.startswith("Android"):
            version_str = self.grab_release_version(state.release)
            verson_bin = self.convert_version_string(version_str)
            cfg_version_bin = self.convert_version_string(scfg.version_android)

            log.debug("Version to check: %s / %s" % (scfg.version_android,
                                                     cfg_version_bin))
            if verson_bin < cfg_version_bin:
                is_old = True
        elif state.os.startswith("iOS"):
            version_str = self.grab_release_version(state.release)
            version_bin = self.convert_version_string(version_str)
            cfg_version_bin = self.convert_version_string(scfg.version_ios)

            log.debug("Version to check: %s / %s" % (scfg.version_ios,
                                                     cfg_version_bin))
            if version_bin < cfg_version_bin:
                is_old = True
        elif state.os.startswith("Win") or state.os.startswith("OSX"):
            cfg_version_bin = self.convert_version_string(scfg.version_pc)

            log.debug("Version to check: %s / %s" % (scfg.version_pc,
                                                     cfg_version_bin))
            if state.version < cfg_version_bin:
                is_old = True
        else:
            if not scfg.check_only_official_pc_packages:
                cfg_version_bin = self.convert_version_string(scfg.version_pc)

                log.debug("Version to check: %s / %s" % (scfg.version_pc,
                                                         cfg_version_bin))
                if state.version < cfg_version_bin:
                    is_old = True

        if is_old:
            if (scfg.kick[0]):
                server.kickUser(state.session, scfg.message % state.name)
            else:
                try:
                    server.sendMessage(state.session,
                                       scfg.message % state.name)
                except self.murmur.InvalidSessionException:
                    log.debug("User disconnected before "
                              "I could change his status.")

    def userDisconnected(self, server, state, context=None): pass

    def userStateChanged(self, server, state, context=None): pass

    def userTextMessage(self, server, user, message, current=None): pass

    def channelCreated(self, server, state, context=None): pass

    def channelRemoved(self, server, state, context=None): pass

    def channelStateChanged(self, server, state, context=None): pass
