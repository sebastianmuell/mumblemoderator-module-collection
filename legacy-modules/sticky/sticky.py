#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2013 – 2017 Natenom <natenom@googlemail.com>
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
                         commaSeperatedBool,
                         MumoModule)
import re

class sticky(MumoModule):
    default_config = {'sticky':(
                        ('servers', commaSeperatedIntegers, []),
                        ),
                        lambda x: re.match('(all)|(server_\d+)', x):(
                        ('canstick', str, 'admin'),
                        ('sticky_group', str, 'stickygroup'),
                        ('sticky_channel', int, 0),
                        ('msg_usergotstick_pm', str, 'You were sticked by %s.'),
                        ('msg_stillsticky_pm', str, "<font style='color:red;font-weight:bold;'>You are still sticked.</font>"),
                        ('msg_usergotstick_global', str, "<font style='color:red;font-weight:bold;'>User %s was sticked by %s.</font>"),
                        ('msg_usergotunsticked_global', str, "<font style='color:red;font-weight:bold;'>User %s was unsticked by %s.</font>"),
                        ('msg_cant_stick_self', str, "<font style='color:red;font-weight:bold;'>You can't stick yourself.</font>"),
                        ('msg_pm_got_sticky', str, "<font style='color:red;font-weight:bold;'>%s sticked you.</font>"),
                        ('msg_cant_stick_while_sticky', str, "<font style='color:red;font-weight:bold;'>While sticked you can't stick another user.</font>"),
                        ('msg_user_already_sticky', str, "<font style='color:red;font-weight:bold;'>User %s is already sticked.</font>"),
                        ('msg_cant_stick_unregistered', str, "<font style='color:red;font-weight:bold;'>You can't stick an unregistered user</font>"),
                        ('cmd_stick', str, '!stick'),
                        ('cmd_listsessions', str, '!sticklist'),
                        ('cmd_unstick', str, '!unstick')
                        )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        sticky.sticky_users={}

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().sticky.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

#    def getUseridBySessionId(self, server, userid):
#	log = self.log()
#	for user in server.getUsers().itervalues():
#	    if (user.userid == userid):
#		log.debug("funktion: %s" % user.session)
#		return user.session

    def userTextMessage(self, server, user, message, current=None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        operator = user

        log = self.log()
        words = re.split(ur"[\u200b\s]+", message.text)
        command = words[0]

        if (command == scfg.cmd_stick) or (command == scfg.cmd_unstick):
            try:
                    if words[1]:
                            targetusersession = words[1]
                            targetuser = server.getState(int(targetusersession))
            except:
                    log.debug("exception for %s" % (words))

        ACL=server.getACL(0)
        for group in ACL[1]:
            if (group.name == scfg.canstick):
                if (operator.userid in group.members):
                    bHasPermission = True
                else:
                    return

        if (command == scfg.cmd_listsessions): #Show operator a list of all sessions connected to the server.
            listusers="<br />Online users: "
            listusers+="<table border='1'><tr><td>SessionID</td><td>Name</td></tr>"
            for iteruser in server.getUsers().itervalues():
                if iteruser.userid > 0: #List registered users only; handling unregistered users is unsupported.
                    listusers+="<tr><td align='right'>%s</td><td>%s</td></tr>" % (iteruser.session, iteruser.name)

            listusers+="</table>"

            listusers+="<br /><br />Users in sticky status:"
            listusers+="<table border='1'><tr><td>SessionID</td><td>Name</td></tr>"

            for guser in server.getUsers().itervalues():
                if (guser.userid in sticky.sticky_users):
                    listusers+="<tr><td>%s</td><td>%s</td></tr>" % (guser.session, guser.name)

            server.sendMessage(operator.session, listusers)
            return

        if (command == scfg.cmd_unstick): #Remove a user out of ST list.
            if (targetuser.session == operator.session): #The bad guy can't remove his own ST status :P.
                log.debug("The bad guy %s tried to remove himself out of sticky status" % targetuser.name)
                return
            else:
                if targetuser.userid in sticky.sticky_users:
                    targetuser.channel=sticky.sticky_users[targetuser.userid]
                    del sticky.sticky_users[targetuser.userid]
                    server.removeUserFromGroup(0, targetuser.session, scfg.sticky_group) #Add user to server group.
                    server.setState(targetuser)
                    server.sendMessageChannel(operator.channel,False, scfg.msg_usergotunsticked_global % (targetuser.name, operator.name))

        if (command == scfg.cmd_stick): #Add a user to ST list.
            if (targetuser.userid < 1):
                server.sendMessage(operator.session, scfg.msg_cant_stick_unregistered)
                return
            if (targetuser.session == user.session): #Nobody should be able to beat himself :P
                server.sendMessage(operator.session, scfg.msg_cant_stick_self)
                return
            if (operator.userid in sticky.sticky_users): #A sticky user, even if admin, should not be able to beat other users while in ST status.
                server.sendMessage(operator.session, scfg.msg_cant_stick_while_sticky)
                return
            if (targetuser.userid in sticky.sticky_users): #If user is already sticky then don't repeat it.
                server.sendMessage(operator.session, scfg.msg_user_already_sticky % (targetuser.name))
                return

            sticky.sticky_users[targetuser.userid] = targetuser.channel #Add user to ST list and remember his current channel.
            targetuser.channel=scfg.sticky_channel
            server.addUserToGroup(0, targetuser.session, scfg.sticky_group) #Add user to server group.
            server.setState(targetuser)
            server.sendMessageChannel(operator.channel,False, scfg.msg_usergotstick_global % (targetuser.name, operator.name))
            server.sendMessage(targetuser.session, scfg.msg_pm_got_sticky % operator.name)

    def userConnected(self, server, state, context = None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        log = self.log()

        if (state.userid in sticky.sticky_users):
            log.debug("User %s is in sticky_group, moving him to sticky_channel and adding him to sticky_group." % (state.name))
            server.addUserToGroup(0, state.session, scfg.sticky_group) #Add user to server group.
            state.channel=scfg.sticky_channel
            server.setState(state) #Move him to ST channel
            server.sendMessage(state.session, scfg.msg_stillsticky_pm)

    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        if (state.userid in sticky.sticky_users) and (state.channel != scfg.sticky_channel):
            state.channel = scfg.sticky_channel
            server.setState(state)

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
