#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2013 – 2017 Natenom <natenom@googlemail.com>
# All rights reserved.
#
# Antirec is based on the scripts onjoin.py, idlemove.py and seen.py
# (made by dd0t) from the Mumble Moderator project , available at
# http://gitorious.org/mumble-scripts/mumo
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
                         commaSeperatedBool,
                         MumoModule)
import pickle
import re

class antirec(MumoModule):
    default_config = {'antirec':(
                            ('servers', commaSeperatedIntegers, []),
                            ('state_before', str, '/tmp/antirec.statebefore_'),
                            ('sessions_allowed', str, '/tmp/antirec.sessions_'),
                        ),
                        lambda x: re.match('(all)|(server_\d+)', x):(
                            ('cantallowself', str, 'You can\'t allow yourself to record.'),
                            ('userremovedfromallowed', str, 'User %s has been removed from list.'),
                            ('userwasnotallowed', str, 'User %s was not on list, can\'t remove.'),
                            ('usergotpermission', str, 'User %s got permission from %s to record.'),
                            ('canallowrecording', str, 'allowrecord'),
                            ('punishment', str, 'DEAF'),
                            ('adminallowself', str, "FALSE"),
                            ('deafmessage', str, 'Recording not allowed. Stop it to get undeafened :)'),
                            ('kickmessage', str, 'Recording not allowed.'),
                            ('listonlinesessions', str, '!list'),
                            ('allowedchannels', str, '1'),
                            ('allowsession', str, '!allow'),
                            ('disallowsession', str, '!disallow'),
                            ('helpcmd', str, '!help')
                        )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()

    def getAllowed(self, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
        try:
            filehandle = open(self.cfg().antirec.sessions_allowed+str(serverid), 'rb')
            allowed=pickle.load(filehandle)
            filehandle.close()
        except:
            allowed={}

        return allowed

    def writeAllowed(self, value, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
        filehandle = open(self.cfg().antirec.sessions_allowed+str(serverid), 'wb')
        pickle.dump(value, filehandle)
        filehandle.close()

    def getStatebefore(self, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
        try:
            filehandle = open(self.cfg().antirec.state_before+str(serverid), 'rb')
            statebefore=pickle.load(filehandle)
            filehandle.close()
        except:
            statebefore={}
        return statebefore

    def writeStatebefore(self, value, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
        filehandle = open(self.cfg().antirec.state_before+str(serverid), 'wb')
        pickle.dump(value, filehandle)
        filehandle.close()

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().antirec.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

    def userTextMessage(self, server, user, message, current=None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all


        #Wenn User Admin, dann weiter, sonst Ende.
        if message.text.startswith(scfg.listonlinesessions) or message.text.startswith(scfg.allowsession) or message.text.startswith(scfg.disallowsession) or message.text.startswith(scfg.helpcmd):
            ACL=server.getACL(0) #Check if user is in group canallowrecording defined in the root channel.

            for gruppe in ACL[1]:
                if (gruppe.name == scfg.canallowrecording):
                    if (user.userid in gruppe.members):
                        #Benutzer ist in der Gruppe
                        if message.text.startswith(scfg.helpcmd):
                            server.sendMessage(user.session, "%s - help<hr />!help - shows this help.<br />!list - shows list of users and allowed recorders.<br />!allow sessionID<br />!disallow sessionID<br />" % __name__)

                        if message.text.startswith(scfg.listonlinesessions):
                            listusers="<br />Online users: "
                            listusers+="<table border='1'><tr><td>SessionID</td><td>Name</td></tr>"
                            for nowuser in server.getUsers().itervalues():

                                listusers+="<tr><td align='right'>%s</td><td>%s</td></tr>" % (nowuser.session, nowuser.name)

                            listusers+="</table>"
                            listusers+="<br /><br />Users with permission to record:"
                            listusers+="<table border='1'><tr><td>SessionID</td><td>Name</td></tr>"
                            for usernow in self.getAllowed(server.id()) :
                                try:
                                    listusers+="<tr><td>%s</td><td>%s</td></tr>" % (usernow, server.getState(int(usernow)).name)
                                except:
                                    #user already disconnected...
                                    pass

                            listusers+="</table>"

                            server.sendMessage(user.session, listusers)

                        if message.text.startswith(scfg.allowsession):
                            usesessionid = message.text[len(scfg.allowsession):].strip()
                            if (str(usesessionid) == str(user.session)) and (scfg.adminallowself == "FALSE"):
                                server.sendMessage(user.session, scfg.cantallowself)
                            else:
                                allowedusers=self.getAllowed(server.id())

                                allowedusers[usesessionid]=1
                                self.writeAllowed(allowedusers, server.id())

                                try:
                                    server.sendMessageChannel(user.channel, False, scfg.usergotpermission % (server.getState(int(usesessionid)).name, user.name))
                                except:
                                    self.log().debug("SessionID %s does not exist :)" % usesessionid)
                                    #server.sendMessageChannel(user.channel, False, "")

                        if message.text.startswith(scfg.disallowsession):
                            usesessionid = message.text[len(scfg.disallowsession):].strip()
                            allowedusers=self.getAllowed(server.id())
                            try:
                                del allowedusers[usesessionid]
                                server.sendMessage(user.session, scfg.userremovedfromallowed % server.getState(int(usesessionid)).name)
                                curuser=server.getState(int(usesessionid))
                                if (curuser.recording==True):
                                    curuser.deaf=True
                                    server.setState(curuser)

                            except:
                                server.sendMessage(user.session, scfg.userwasnotallowed % usesessionid)

                            self.writeAllowed(allowedusers, server.id())

                        break

    def userConnected(self, server, state, context = None): pass
    def userDisconnected(self, server, state, context = None):
        allowedusers=self.getAllowed(server.id())
        if str(state.session) in allowedusers:
            del allowedusers[str(state.session)]
            self.log().debug("Session %s removed from allowedusers, %s disconnected" % (state.session, state.name))
            self.writeAllowed(allowedusers, server.id())


    def userStateChanged(self, server, state, context = None):
        """Wer aufnimmt, wird stumm-taub gestellt."""
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        allowedchannels_list=scfg.allowedchannels.split()
        if str(state.channel) in allowedchannels_list: #recording in these channels is allowed
                return

        list_state_before_recording=self.getStatebefore(server.id())

        if (state.recording==True) and (state.deaf==False):
            allowedtorecord=self.getAllowed(server.id())
            list_state_before_recording[state.session]=state.deaf
            if not (str(state.session) in allowedtorecord):
                if (scfg.punishment=="DEAF"):
                    state.deaf=True
                    server.setState(state)

                    server.sendMessageChannel(state.channel, False, scfg.deafmessage % (state.name))
                elif (scfg.punishment=="KICK"):
                    server.kickUser(state.session, scfg.kickmessage)

        #Wenn Benutzer in der Liste drin ist, hat er irgendwann aufgenommen; wenn er jetzt nicht mehr aufnimmt, bekommt er den deaf-Status von vor der Aufnahme :)
        if (state.recording==False) and (state.session in list_state_before_recording):
            state.deaf = list_state_before_recording[state.session]
            state.mute = list_state_before_recording[state.session]
            server.setState(state)

            del list_state_before_recording[state.session]

        self.writeStatebefore(list_state_before_recording, str(server.id()))

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
