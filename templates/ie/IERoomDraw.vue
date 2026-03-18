<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">Room Draw — Round {{ roundNumber }}</h5>
      <span class="badge badge-info">{{ rooms.length }} rooms</span>
    </div>

    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border text-primary"></span>
    </div>

    <table v-else class="table table-hover table-sm table-striped">
      <thead class="thead-light">
        <tr>
          <th>Room #</th>
          <th>Judge</th>
          <th>Entries</th>
          <th>Status</th>
          <th v-if="isDirector"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="room in rooms" :key="room.id">
          <td class="font-weight-bold">{{ room.room_number }}</td>
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
            <button v-if="!room.confirmed"
                    class="btn btn-outline-success btn-sm"
                    :disabled="confirmingRoom === room.id"
                    @click="confirmRoom(room.id)">
              <span v-if="confirmingRoom === room.id"
                    class="spinner-border spinner-border-sm"></span>
              Confirm
            </button>
          </td>
        </tr>
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
    }
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
        var resp = await fetch(
          this.apiBase() + '/draw/' + this.eventId + '/round/' + this.roundNumber + '/'
        )
        if (!resp.ok) throw new Error('Failed to load draw')
        var data = await resp.json()
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
        var token = window.ieConfig ? window.ieConfig.token : ''
        var resp = await fetch(this.apiBase() + '/ballots/' + roomId + '/confirm/', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token },
        })
        if (!resp.ok) {
          var body = await resp.json()
          this.error = body.detail || 'Confirm failed'
          return
        }
        // Update local state
        var room = this.rooms.find(function (r) { return r.id === roomId })
        if (room) room.confirmed = true
      } catch (e) {
        this.error = e.message
      } finally {
        this.confirmingRoom = null
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
      // Pass JWT token for authenticated WebSocket connections
      var token = window.ieConfig ? window.ieConfig.token : ''
      if (token) {
        url += '?token=' + encodeURIComponent(token)
      }
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
