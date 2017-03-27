#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
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

# sticky.py - see README

from mumo_module import (commaSeperatedIntegers,
                         commaSeperatedStrings,
                         commaSeperatedBool,
                         MumoModule)
import re

class sticky(MumoModule):
    default_config = {'sticky':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(
                                ('canstick', commaSeperatedStrings, ["admin", "moderator"]),
                                ('sticky_group', str, 'stickygroup'),
                                ('sticky_channel', int, 0),
                                ('msg_usergotstick_pm', str, 'You were sticked by %s.'),
                                ('msg_stillsticky_pm', str, "<font style='color:red;font-weight:bold;'>You are still sticked.</font>"),
                                ('msg_usergotstick_global', str, "<font style='color:red;font-weight:bold;'>User %s was sticked by %s.</font>"),
                                ('msg_usergotunsticked_global', str, "<font style='color:red;font-weight:bold;'>User %s was unsticked by %s.</font>"),
                                ('msg_cant_stick_self', str, "<font style='color:red;font-weight:bold;'>You can't stick yourself.</font>"),
                                ('msg_pm_got_sticky', str, "<font style='color:red;font-weight:bold;'>%s sticked you.</font>"),
                                ('msg_cant_stick_while_sticky', str, "<font style='color:red;font-weight:bold;'>While sticked you can't stick another user.<font>"),
                                ('msg_user_already_sticky', str, "<font style='color:red;font-weight:bold;'>User %s is already sticked.</font>"),
                                ('msg_cant_stick_unregistered', str, "<font style='color:red;font-weight:bold;'>You can't stick an unregistered user</font>")
                                )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()

        self.action_stick_user = manager.getUniqueAction()
        self.action_unstick_user = manager.getUniqueAction()
        self.action_list_sticked = manager.getUniqueAction()

        self.sticky_users={}

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().sticky.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

        # Craft the array for all virtual servers. Should also work for server later started servers.
        meta = manager.getMeta()
        servers = meta.getAllServers()

        for virtualserver in servers:
            if not virtualserver.id() in self.sticky_users:
                self.sticky_users[virtualserver.id()] = {}

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

    def __on_list_sticked(self, server, action, user, target):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        assert action == self.action_list_sticked

        if len(self.sticky_users[server.id()]) > 0:
            listusers="<span style='color:red;'>Currently sticked users:</span>"
            listusers+="<ul>"

            for usernow in self.sticky_users[server.id()] :
                ureg = server.getRegistration(usernow)
                if ureg:
                    listusers+="<li>%s</li>" % ureg[self.murmur.UserInfo.UserName]

            listusers+="</ul>"
        else:
            listusers="There are currently no sticked users."

        server.sendMessage(user.session, listusers)

    def __on_stick_user(self, server, action, user, target):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        assert action == self.action_stick_user

        if (target.userid < 1):
            server.sendMessage(user.session, scfg.msg_cant_stick_unregistered)
            return
        if (target.session == user.session): #Nobody should be able to beat himself :P
            server.sendMessage(user.session, scfg.msg_cant_stick_self)
            return
        if (user.userid in self.sticky_users[server.id()]): #A sticky user, even if admin, should not be able to beat other users while in ST status.
            server.sendMessage(user.session, scfg.msg_cant_stick_while_sticky)
            return
        if (target.userid in self.sticky_users[server.id()]): #If user is already sticky then don't repeat it.
            server.sendMessage(user.session, scfg.msg_user_already_sticky % (target.name))
            return

        self.sticky_users[server.id()][target.userid] = target.channel #Add user to ST list and remember his current channel.
        target.channel=scfg.sticky_channel
        server.addUserToGroup(0, target.session, scfg.sticky_group) #Add user to server group.
        server.setState(target)
        server.sendMessageChannel(user.channel,False, scfg.msg_usergotstick_global % (target.name, user.name))
        server.sendMessage(target.session, scfg.msg_pm_got_sticky % user.name)

    def __on_unstick_user(self, server, action, user, target):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        assert action == self.action_unstick_user

        log = self.log()

        if (target.session == user.session): #The bad guy can't remove his own ST status :P.
                log.debug("The bad guy %s tried to remove himself out of sticky status" % target.name)
                return
        else:
                if target.userid in self.sticky_users[server.id()]:
                        target.channel=self.sticky_users[server.id()][target.userid]
                        del self.sticky_users[server.id()][target.userid]
                        server.removeUserFromGroup(0, target.session, scfg.sticky_group) #Add user to server group.
                        server.setState(target)
                        server.sendMessageChannel(user.channel,False, scfg.msg_usergotunsticked_global % (target.name, user.name))

    def userTextMessage(self, server, user, message, current=None): pass

    def userConnected(self, server, user, context = None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        log = self.log()
        manager = self.manager()
        bHasPermission = False

        if (user.userid in self.sticky_users[server.id()]):
            log.debug("User %s is in sticky_group, moving him to sticky_channel and adding him to sticky_group." % (user.name))
            server.addUserToGroup(0, user.session, scfg.sticky_group) #Add user to server group.
            user.channel=scfg.sticky_channel
            server.setState(user) #Move him to ST channel
            server.sendMessage(user.session, scfg.msg_stillsticky_pm)
        else:
            # Check whether user has permission to stick users and add context menu entries.
            ACL=server.getACL(0)
            for group in ACL[1]:
                if (group.name in scfg.canstick):
                    if (user.userid in group.members):
                        bHasPermission = True
                        # We can't break here as there can be definied multiple groups.

            if bHasPermission:
                manager.addContextMenuEntry(
                        server, # Server of user
                        user, # User which should receive the new entry
                        self.action_stick_user, # Identifier for the action
                        "Stick this user", # Text in the client
                        self.__on_stick_user, # Callback called when user uses the entry
                        self.murmur.ContextUser # We only want to show this entry on users
                )

                manager.addContextMenuEntry(
                        server, # Server of user
                        user, # User which should receive the new entry
                        self.action_unstick_user, # Identifier for the action
                        "Unstick this user", # Text in the client
                        self.__on_unstick_user, # Callback called when user uses the entry
                        self.murmur.ContextUser # We only want to show this entry on users
                )

                manager.addContextMenuEntry(
                        server, # Server of user
                        user, # User which should receive the new entry
                        self.action_list_sticked, # Identifier for the action
                        "List sticked users", # Text in the client
                        self.__on_list_sticked, # Callback called when user uses the entry
                        self.murmur.ContextServer # We only want to show this entry on users
                )

            else:
                return

    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        if (state.userid in self.sticky_users[server.id()]) and (state.channel != scfg.sticky_channel):
            state.channel = scfg.sticky_channel
            server.setState(state)

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
