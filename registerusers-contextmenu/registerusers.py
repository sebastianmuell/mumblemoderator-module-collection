#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2017 Natenom <natenom@googlemail.com>
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
                         commaSeperatedStrings,
                         commaSeperatedBool,
                         MumoModule)
import re
import Murmur
from hashlib import sha1

class registerusers(MumoModule):
    default_config = {'registerusers':(
                        ('servers', commaSeperatedIntegers, []),
                        ),
                        lambda x: re.match('(all)|(server_\d+)', x):(
                        ('canregister', commaSeperatedStrings, ["admin", "moderator"]),
                        ('msg_success', str, "<font style='color:green;font-weight:bold;'>User was registered. Though he needs to reconnect now."),
                        ('msg_success_target', str, "<font style='color:green;font-weight:bold;'>You are registered now. Though you need to reconnect to get your registration icon."),
                        ('msg_error', str, "<font style='color:red;font-weight:bold;'>Something did not work, tell your admin :)</font>"),
                        ('msg_no_certifcate', str, "<font style='color:red;font-weight:bold;'>Cannot register the user because he does not provide a certificate.</font>"),
                        ('msg_already_registered', str, "<font style='color:red;font-weight:bold;'>This user is already registered, idiot :)</font>"),
                        ('contextmenu_text', str, "Register this user on our Server")
                        )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        self.action_register_user = manager.getUniqueAction()

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().registerusers.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

    def __on_register_user(self, server, action, user, target):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        assert action == self.action_register_user

        if (target.userid > 0):
            server.sendMessage(user.session, scfg.msg_already_registered)
        else:
            userCert = server.getCertificateList(target.session)
            userHash = sha1(userCert[0]).hexdigest()
            userInfomap = {Murmur.UserInfo.UserName: target.name, Murmur.UserInfo.UserHash: userHash}
            try:
                server.registerUser(userInfomap)
                server.sendMessage(user.session, scfg.msg_success)
                server.sendMessage(target.session, scfg.msg_success_target)
            except:
                server.sendMessage(user.session, scfg.msg_error)

    def userTextMessage(self, server, user, message, current=None): pass

    def userConnected(self, server, user, context = None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        log = self.log()
        manager = self.manager()
        bHasPermission = False

        # Check whether user has permission to register users and add context menu entries.
        ACL=server.getACL(0)
        for group in ACL[1]:
            if (group.name in scfg.canregister):
                if (user.userid in group.members):
                    bHasPermission = True
                    # We can't break here as there can be definied multiple groups.

        if bHasPermission:
            self.log().info("Adding menu entries for user" + user.name)

            manager.addContextMenuEntry(
                    server, # Server of user
                    user, # User which should receive the new entry
                    self.action_register_user, # Identifier for the action
                    scfg.contextmenu_text, # Text in the client
                    self.__on_register_user, # Callback called when user uses the entry
                    self.murmur.ContextUser # We only want to show this entry on users
            )

    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None): pass
    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
