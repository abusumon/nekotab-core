<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">Room Draw — Round {{ roundNumber }}</h5>
      <div>
        <a v-if="isDirector" :href="judgeLinksUrl"
           class="btn btn-outline-info btn-sm mr-2">Judge Links</a>
        <span class="badge badge-info">{{ rooms.length }} rooms</span>
      </div>
    </div>

    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border text-primary"></span>
    </div>

    <table v-else class="table table-hover table-sm table-striped">
      <thead class="thead-light">
        <tr>
          <th>Room #</th>
          <th>Name</th>
          <th>Judge</th>
          <th>Entries</th>
          <th>Status</th>
          <th v-if="isDirector"></th>
        </tr>
      </thead>
      <tbody>
        <template v-for="room in rooms">
          <tr :key="room.id">
            <td class="font-weight-bold">{{ room.room_number }}</td>
            <td>
              <template v-if="isDirector">
                <div v-if="renamingRoomId === room.id" class="d-flex align-items-center">
                  <input v-model="renameValue" type="text" maxlength="100"
                         class="form-control form-control-sm" style="width: 140px"
                         placeholder="e.g. Room 101"
                         @keyup.enter="saveRoomName(room)"
                         @keyup.escape="renamingRoomId = null" />
                  <button class="btn btn-sm btn-outline-success ml-1" :disabled="renamingSaving"
                          @click="saveRoomName(room)">&#10003;</button>
                  <button class="btn btn-sm btn-outline-secondary ml-1"
                          @click="renamingRoomId = null">&times;</button>
                </div>
                <span v-else class="text-primary" style="cursor:pointer; border-bottom: 1px dashed #007bff"
                      @click="startRename(room)">
                  {{ room.nickname || '—' }}
                </span>
              </template>
              <template v-else>
                {{ room.nickname || '—' }}
              </template>
            </td>
            <td>
              <span v-if="room.judge_name">{{ room.judge_name }}</span>
              <span v-else class="text-muted">Unassigned</span>
            </td>
            <td>
              <span v-for="(entry, idx) in room.entries" :key="entry.id">
                {{ entry.speaker_name }}
                <small class="text-muted">({{ entry.institution_code }})</small>
                <span v-if="idx < room.entries.length - 1">, </span>
              </span>
            </td>
            <td>
              <span class="badge"
                    :class="ballotBadgeClass(room)">
                {{ ballotLabel(room) }}
              </span>
            </td>
            <td v-if="isDirector">
              <button v-if="!room.confirmed && ballotLabel(room) !== 'No Ballot'"
                      class="btn btn-outline-success btn-sm mr-1"
                      :disabled="confirmingRoom === room.id"
                      @click="confirmRoom(room.id)">
                <span v-if="confirmingRoom === room.id"
                      class="spinner-border spinner-border-sm"></span>
                Confirm
              </button>
              <button v-if="hasBallot(room)"
                      class="btn btn-outline-secondary btn-sm"
                      @click="toggleBallotEdit(room)">
                {{ editingRoomId === room.id ? 'Cancel' : 'Edit Ballot' }}
              </button>
            </td>
          </tr>
          <!-- Inline Ballot Edit Row -->
          <tr v-if="editingRoomId === room.id" :key="'edit-' + room.id">
            <td :colspan="isDirector ? 6 : 5">
              <div class="border rounded p-3 bg-light">
                <div v-if="editLoading" class="text-center py-2">
                  <span class="spinner-border spinner-border-sm"></span> Loading results...
                </div>
                <div v-else>
                  <table class="table table-sm table-bordered mb-2">
                    <thead class="thead-light">
                      <tr>
                        <th>Competitor</th>
                        <th style="width:100px">Rank</th>
                        <th style="width:120px">Speaker Pts</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="r in editResults" :key="r.id">
                        <td>{{ r.speaker_name }} <small class="text-muted">({{ r.institution_code }})</small></td>
                        <td>
                          <input v-model.number="r.rank" type="number" min="1"
                                 class="form-control form-control-sm" />
                        </td>
                        <td>
                          <input v-model.number="r.speaker_points" type="number"
                                 min="0" max="30" step="0.5"
                                 class="form-control form-control-sm" />
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <div v-if="editError" class="alert alert-danger py-1 small">{{ editError }}</div>
                  <div v-if="editSuccess" class="alert alert-success py-1 small">{{ editSuccess }}</div>
                  <button class="btn btn-primary btn-sm" :disabled="editSaving" @click="saveBallotEdit(room)">
                    <span v-if="editSaving" class="spinner-border spinner-border-sm mr-1"></span>
                    Save Changes
                  </button>
                </div>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'IERoomDraw',
  props: {
    eventId: { type: Number, required: true },
    roundNumber: { type: Number, required: true },
    isDirector: { type: Boolean, default: false },
  },
  data () {
    return {
      rooms: [],
      loading: true,
      error: '',
      confirmingRoom: null,
      ws: null,
      // Ballot edit state
      editingRoomId: null,
      editResults: [],
      editLoading: false,
      editSaving: false,
      editError: '',
      editSuccess: '',
      // Room rename state
      renamingRoomId: null,
      renameValue: '',
      renamingSaving: false,
    }
  },
  computed: {
    judgeLinksUrl () {
      var cfg = window.ieConfig || {}
      var slug = cfg.tournamentSlug || ''
      var prefix = slug ? ('/' + slug) : ''
      return prefix + '/admin/ie/' + this.eventId + '/judge-links/' + this.roundNumber + '/page/'
    },
  },
  mounted () {
    this.fetchDraw()
    this.connectWebSocket()
  },
  beforeDestroy () {
    if (this.ws) {
      this.ws.close()
    }
  },
  methods: {
    apiBase () {
      var cfg = window.ieConfig || {}
      return (window.NEKOSPEECH_URL || cfg.apiBaseUrl || '/api/ie').replace(/\/$/, '')
    },
    async apiFetch (url, options) {
      options = options || {}
      var cfg = window.ieConfig || {}
      var headers = Object.assign({}, options.headers || {})
      if (cfg.apiKey) headers['X-IE-Api-Key'] = cfg.apiKey
      if (options.body) headers['Content-Type'] = 'application/json'

      var response
      try {
        response = await fetch(this.apiBase() + url, Object.assign({}, options, { headers: headers }))
      } catch (networkErr) {
        throw new Error('Cannot reach IE service. Is nekospeech running? (' + networkErr.message + ')')
      }

      if (!response.ok) {
        var detail = 'HTTP ' + response.status
        try {
          var errData = await response.json()
          detail = errData.detail || errData.message || detail
        } catch (_) {
          if (response.status === 403) detail = 'Authentication failed — check NEKOSPEECH_IE_API_KEY'
          else if (response.status === 404) detail = 'Endpoint not found — check NEKOSPEECH_URL'
          else if (response.status === 502) detail = 'IE service is down — check the nekospeech service logs'
          else detail = 'Server error ' + response.status
        }
        throw new Error(detail)
      }

      return response.json()
    },
    hasBallot (room) {
      var status = room.ballot_status || (room.confirmed ? 'confirmed' : 'no_ballot')
      return status === 'submitted' || status === 'confirmed'
    },
    ballotBadgeClass (room) {
      var status = room.ballot_status || (room.confirmed ? 'confirmed' : 'no_ballot')
      if (status === 'confirmed') return 'badge-success'
      if (status === 'submitted') return 'badge-info'
      return 'badge-secondary'
    },
    ballotLabel (room) {
      var status = room.ballot_status || (room.confirmed ? 'confirmed' : 'no_ballot')
      if (status === 'confirmed') return 'Confirmed'
      if (status === 'submitted') return 'Submitted'
      return 'No Ballot'
    },
    async fetchDraw () {
      this.loading = true
      try {
        var data = await this.apiFetch('/draw/' + this.eventId + '/round/' + this.roundNumber + '/')
        this.rooms = data.rooms || []
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async confirmRoom (roomId) {
      this.confirmingRoom = roomId
      this.error = ''
      try {
        await this.apiFetch('/ballots/' + roomId + '/confirm/', {
          method: 'POST',
        })
        // Update local state
        var room = this.rooms.find(function (r) { return r.id === roomId })
        if (room) {
          room.confirmed = true
          room.ballot_status = 'confirmed'
        }
      } catch (e) {
        this.error = e.message
      } finally {
        this.confirmingRoom = null
      }
    },
    // Ballot edit methods
    async toggleBallotEdit (room) {
      if (this.editingRoomId === room.id) {
        this.editingRoomId = null
        return
      }
      this.editingRoomId = room.id
      this.editError = ''
      this.editSuccess = ''
      this.editLoading = true
      try {
        this.editResults = await this.apiFetch('/ballots/' + room.id + '/')
      } catch (e) {
        this.editError = e.message
        this.editResults = []
      } finally {
        this.editLoading = false
      }
    },
    async saveBallotEdit (room) {
      this.editSaving = true
      this.editError = ''
      this.editSuccess = ''
      try {
        // If room is confirmed, unconfirm first
        if (room.confirmed) {
          await this.apiFetch('/ballots/' + room.id + '/unconfirm/', { method: 'POST' })
          room.confirmed = false
          room.ballot_status = 'submitted'
        }
        // Re-submit the full ballot
        var payload = {
          room_id: room.id,
          results: this.editResults.map(function (r) {
            return { entry_id: r.entry_id, rank: r.rank, speaker_points: r.speaker_points }
          }),
        }
        await this.apiFetch('/ballots/submit/', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        this.editSuccess = 'Ballot updated.'
      } catch (e) {
        this.editError = e.message
      } finally {
        this.editSaving = false
      }
    },
    startRename (room) {
      this.renamingRoomId = room.id
      this.renameValue = room.nickname || ''
    },
    async saveRoomName (room) {
      this.renamingSaving = true
      try {
        var updated = await this.apiFetch('/draw/rename-room/', {
          method: 'POST',
          body: JSON.stringify({ room_id: room.id, nickname: this.renameValue || null }),
        })
        room.nickname = updated.nickname
        this.renamingRoomId = null
      } catch (e) {
        this.error = e.message
      } finally {
        this.renamingSaving = false
      }
    },
    connectWebSocket () {
      var tournamentId = window.ieConfig ? window.ieConfig.tournamentId : null
      if (!tournamentId) return

      var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      var base = this.apiBase()
      // For WebSocket, derive host from the API base URL
      var wsBase
      if (base.indexOf('http') === 0) {
        wsBase = base.replace(/^http/, 'ws')
      } else {
        wsBase = protocol + '//' + window.location.host + base
      }
      var url = wsBase + '/ws/tournament/' + tournamentId + '/'
      this.ws = new WebSocket(url)

      var self = this
      this.ws.onmessage = function (event) {
        var msg = JSON.parse(event.data)
        if (msg.type === 'room_confirmed') {
          var room = self.rooms.find(function (r) { return r.id === msg.room_id })
          if (room) {
            room.confirmed = true
            room.ballot_status = 'confirmed'
          }
        }
        if (msg.type === 'ballot_submitted') {
          var room2 = self.rooms.find(function (r) { return r.id === msg.room_id })
          if (room2 && !room2.confirmed) {
            room2.ballot_status = 'submitted'
          }
        }
        if (msg.type === 'room_draw_ready' && msg.round === self.roundNumber) {
          self.fetchDraw()
        }
      }
      this.ws.onclose = function () {
        // Reconnect after 3 seconds
        setTimeout(function () { self.connectWebSocket() }, 3000)
      }
    },
  },
}
</script>
