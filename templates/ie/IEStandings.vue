<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">Standings</h5>
      <div>
        <span class="badge badge-info mr-2">{{ standings.rounds_complete }} rounds</span>
        <button class="btn btn-outline-secondary btn-sm" @click="exportCsv">
          ↓ Export CSV
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border text-primary"></span>
    </div>

    <div v-else-if="standings.entries.length === 0"
         class="alert alert-secondary text-center">
      No standings data yet. Results will appear after rooms are confirmed.
    </div>

    <table v-else class="table table-hover table-sm table-striped">
      <thead class="thead-light">
        <tr>
          <th style="width:60px">#</th>
          <th>Name</th>
          <th>School</th>
          <th class="text-right">Trunc. Rank</th>
          <th class="text-right">Speaker Pts</th>
          <th class="text-right">Rounds</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in standings.entries" :key="row.entry_id">
          <td class="font-weight-bold">{{ row.rank }}</td>
          <td>{{ row.speaker_name }}</td>
          <td>
            {{ row.institution_name }}
            <small class="text-muted">({{ row.institution_code }})</small>
          </td>
          <td class="text-right">{{ row.truncated_rank_sum }}</td>
          <td class="text-right">{{ row.total_speaker_points }}</td>
          <td class="text-right">{{ row.rounds_competed }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  name: 'IEStandings',
  props: {
    eventId: { type: Number, required: true },
  },
  data () {
    return {
      standings: { event_id: 0, rounds_complete: 0, entries: [] },
      loading: true,
      ws: null,
    }
  },
  mounted () {
    this.fetchStandings()
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
          else if (response.status === 502) detail = 'IE service is down — check nekospeech on Heroku'
          else detail = 'Server error ' + response.status
        }
        throw new Error(detail)
      }

      return response.json()
    },
    async fetchStandings () {
      this.loading = true
      try {
        this.standings = await this.apiFetch('/standings/' + this.eventId + '/')
      } catch (_e) {
        this.standings = { event_id: this.eventId, rounds_complete: 0, entries: [] }
      } finally {
        this.loading = false
      }
    },
    exportCsv () {
      var url = this.apiBase() + '/standings/' + this.eventId + '/export/?format=csv'
      window.open(url, '_blank')
    },
    connectWebSocket () {
      var tournamentId = window.ieConfig ? window.ieConfig.tournamentId : null
      if (!tournamentId) return

      var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      var base = this.apiBase()
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
        if (msg.type === 'standings_updated' && msg.event_id === self.eventId) {
          self.fetchStandings()
        }
      }
      this.ws.onclose = function () {
        setTimeout(function () { self.connectWebSocket() }, 3000)
      }
    },
  },
}
</script>
