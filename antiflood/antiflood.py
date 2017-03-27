#!/usr/bin/env python
# -*- coding: utf-8
#
# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2012 - 2017 Natenom <natenom@googlemail.com>
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
#
#
# antiflood.py
# Kick users after maxactions actions within timeframe.

from mumo_module import (commaSeperatedIntegers,
                            commaSeperatedBool,
                            MumoModule)
from random import randint
import re,time

class antiflood(MumoModule):
    default_config = {'antiflood':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(
                                ('maxactions', int, 10),
                                ('timeframe', int, 20),
                                ('random_kick_threshold', int, 9),
                                ('randomize', commaSeperatedBool, [True]),
                                ('probability_to_act_before_limit', int, 90),
                                ('number_of_actions_until_act_before_limit', int, 90),
                                ('excluded_from_antiflood', str, 'excludedfromantiflood'),
                                ('kickmessage', str, 'Please do not spam :)'),
                                ('kickmessagerandomize', str, 'Oh, did I miscount?'),
                                ('defaultroombeforekick', int, 1),
                                ('warnmessage', str, 'WARNING: Spam control system is active; you reached %d of %d actions within %d seconds.')
                        )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        self.data = {}

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().antiflood.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #
    def userTextMessage(self, server, user, message, current=None):
        self.handleSpam(server, server.getState(user.session))

    def userConnected(self, server, state, context = None): pass
    def userDisconnected(self, server, state, context = None):
        sid = server.id()

        users_timestamps = self.data[sid][0]
        users_counts = self.data[sid][1]

        try:
            if state.session in users_timestamps:
                log = self.log()
                del users_timestamps[state.session]
                del users_counts[state.session]
                log.debug("Removed session %s from antiflood control system." % state.session)
        except KeyError:
            log.debug("Removed session %s from antiflood control system." % state.session)

    def userStateChanged(self, server, state, context = None):
        self.handleSpam(server, state)

    def handleSpam(self, server, state):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        do_handle = True
        ACL=server.getACL(0) #Check if user is in group excluded_from_antiflood defined in the root channel.

        for group in ACL[1]:
            if (group.name == scfg.excluded_from_antiflood):
                if (state.userid in group.members):
                    #Do not handle user
                    do_handle = False
                    break

        if do_handle:
            log = self.log()

            sid = server.id()
            if sid not in self.data: #Create new object for this server
                count = {} #Count of actions
                ts = {} #Timestamp of last command
                self.data[sid] = [] #New list for sid
                self.data[sid].append(ts) #Accessible through self.data[sid][0]
                self.data[sid].append(count) #Accessible through self.data[sid][1]

            users_timestamps = self.data[sid][0]
            users_counts = self.data[sid][1]

            #log.debug(users_timestamps)

            if state.session in users_counts:
                log.debug("Recorded actions for session %s: %s" % (state.session, users_counts[state.session]))

            timenow = time.time()

            if state.session in users_timestamps:
                if (timenow - users_timestamps[state.session] <= scfg.timeframe):
                    users_counts[state.session] = users_counts[state.session] + 1

                    random_kick = 0

                    if users_counts[state.session] >= int(scfg.maxactions/2) and users_counts[state.session] <= scfg.maxactions:
                        try:
                            server.sendMessage(state.session, scfg.warnmessage % (users_counts[state.session], scfg.maxactions, scfg.timeframe))
                        except:
                            log.debug("Warning: Invalid session exception for session %s. User probably already disconnected." % state.session)

                        if scfg.randomize:
                            random_kick = randint(1,10)
                            log.debug("Randomkick int for session %i is %i. random_kick_threshold is %i." % (state.session, random_kick, scfg.random_kick_threshold))

                    if (users_counts[state.session] > scfg.maxactions) or (random_kick >= scfg.random_kick_threshold):
                        try:
                            if scfg.defaultroombeforekick == 1:
                                    state.channel = int(server.getConf("defaultchannel"))
                                    server.setState(state)

                            if random_kick >= scfg.random_kick_threshold:
                                server.kickUser(state.session, scfg.kickmessagerandomize)
                            else:
                                server.kickUser(state.session, scfg.kickmessage)
                        except:
                            log.debug("Warning: Invalid session exception for session %s. User probably already disconnected." % state.session)
                else:
                    users_counts[state.session] = 1
                    users_timestamps[state.session] = timenow
            else:
                log.debug("New user added to antiflood control system. Server ID: %s, Session ID: %s." % (sid, state.session))
                users_timestamps[state.session] = timenow
                users_counts[state.session] = 1

    def channelCreated(self, server, state, context = None): pass
        #self.handleSpam(server, state)
    def channelRemoved(self, server, state, context = None): pass
        #self.handleSpam(server, state)
    def channelStateChanged(self, server, state, context = None): pass
        #self.handleSpam(server, state)
