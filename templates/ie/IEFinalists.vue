<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h5 class="mb-0">Finals Advancement</h5>
        <small class="text-muted">After {{ roundsComplete }} prelim round{{ roundsComplete !== 1 ? 's' : '' }}</small>
      </div>
    </div>

    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border spinner-border-sm mr-1"></span> Loading standings...
    </div>

    <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

    <div v-else-if="standings.length === 0" class="alert alert-info">
      No standings data yet. Complete prelim rounds to see finalists.
    </div>

    <div v-else>
      <!-- Cutoff control -->
      <div class="d-flex align-items-center mb-3">
        <label class="font-weight-bold small mb-0 mr-2">Finalists cutoff:</label>
        <input v-model.number="cutoff" type="number" min="1"
               :max="standings.length" style="width:70px"
               class="form-control form-control-sm mr-2" />
        <span class="text-muted small">entries advance to finals</span>
      </div>

      <!-- Standings table with cutoff -->
      <table class="table table-sm table-hover">
        <thead class="thead-light">
          <tr>
            <th style="width:50px">#</th>
            <th>Name</th>
            <th>School</th>
            <th class="text-right">TR</th>
            <th class="text-right">SP</th>
            <th style="width:120px">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in standings" :key="row.entry_id"
              :class="rowClass(idx)">
            <td class="font-weight-bold">{{ row.rank }}</td>
            <td>{{ row.speaker_name }}</td>
            <td>
              {{ row.institution_name }}
              <small class="text-muted">({{ row.institution_code }})</small>
            </td>
            <td class="text-right">{{ row.truncated_rank_sum }}</td>
            <td class="text-right">{{ row.total_speaker_points }}</td>
            <td>
              <span v-if="idx < cutoff" class="badge badge-success">FINALIST</span>
              <span v-else class="text-muted small">Not advancing</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Generate Finals Draw -->
      <div v-if="cutoff > 0" class="mt-3">
        <hr />
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <strong>{{ cutoff }}</strong> entries will compete in finals round.
          </div>
          <button class="btn btn-primary btn-sm" :disabled="generating" @click="generateFinalsDraw">
            <span v-if="generating" class="spinner-border spinner-border-sm mr-1"></span>
            {{ generating ? 'Generating...' : 'Generate Finals Draw' }}
          </button>
        </div>
        <div v-if="genError" class="alert alert-danger mt-2 py-2">{{ genError }}</div>
        <div v-if="genSuccess" class="alert alert-success mt-2 py-2">{{ genSuccess }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IEFinalists',
  data () {
    return {
      standings: [],
      roundsComplete: 0,
      numRounds: 3,
      cutoff: 6,
      loading: true,
      error: '',
      generating: false,
      genError: '',
      genSuccess: '',
    }
  },
  computed: {
    cfg () { return window.ieConfig || {} },
    eventId () { return this.cfg.eventId },
    pathPrefix () {
      return this.cfg.tournamentSlug ? ('/' + this.cfg.tournamentSlug) : ''
    },
    finalistEntryIds () {
      return this.standings.slice(0, this.cutoff).map(function (r) { return r.entry_id })
    },
  },
  mounted () {
    this.numRounds = this.cfg.numRounds || 3
    this.fetchStandings()
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
        throw new Error('Cannot reach IE service. (' + networkErr.message + ')')
      }

      if (!response.ok) {
        var detail = 'HTTP ' + response.status
        try {
          var errData = await response.json()
          detail = errData.detail || errData.message || detail
        } catch (_) {}
        throw new Error(detail)
      }

      return response.json()
    },
    rowClass (idx) {
      if (idx < this.cutoff) return ''
      if (idx === this.cutoff) return 'border-top border-danger'
      return 'text-muted'
    },
    async fetchStandings () {
      this.loading = true
      this.error = ''
      try {
        var data = await this.apiFetch('/standings/' + this.eventId + '/')
        this.standings = data.entries || []
        this.roundsComplete = data.rounds_complete || 0
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async generateFinalsDraw () {
      this.generating = true
      this.genError = ''
      this.genSuccess = ''
      try {
        var finalsRound = this.numRounds + 1
        await this.apiFetch('/draw/generate/', {
          method: 'POST',
          body: JSON.stringify({
            event_id: this.eventId,
            round_number: finalsRound,
            finalist_entry_ids: this.finalistEntryIds,
          }),
        })
        this.genSuccess = 'Finals draw generated for Round ' + finalsRound + '!'
      } catch (e) {
        this.genError = e.message
      } finally {
        this.generating = false
      }
    },
  },
}
</script>
