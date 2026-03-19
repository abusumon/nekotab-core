<template>
  <div>
    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border spinner-border-sm mr-1"></span> Loading events...
    </div>

    <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

    <div v-else-if="events.length === 0" class="alert alert-info">
      No events have been created yet.
      <a :href="setupUrl" class="alert-link">Create your first event</a>.
    </div>

    <div v-else>
      <div class="table-responsive">
        <table class="table table-hover table-sm">
          <thead>
            <tr>
              <th>Event</th>
              <th>Type</th>
              <th>Rounds</th>
              <th>Room Size</th>
              <th>Entries</th>
              <th>Draws</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ev in events" :key="ev.id">
              <td>
                <strong>{{ ev.name }}</strong>
                <span class="text-muted ml-1">({{ ev.abbreviation }})</span>
              </td>
              <td>{{ eventLabel(ev.event_type) }}</td>
              <td>{{ ev.num_rounds }}</td>
              <td>{{ ev.room_size }}</td>
              <td>{{ ev.entry_count }}</td>
              <td>
                <span v-if="ev.rounds_with_draw && ev.rounds_with_draw.length">
                  {{ ev.rounds_with_draw.join(', ') }}
                </span>
                <span v-else class="text-muted">—</span>
              </td>
              <td>
                <a v-for="rd in availableRounds(ev)" :key="rd"
                   :href="drawUrl(ev.id, rd)"
                   class="btn btn-outline-primary btn-sm mr-1 mb-1">
                  R{{ rd }}
                </a>
                <a :href="standingsUrl(ev.id)"
                   class="btn btn-outline-secondary btn-sm mb-1">
                  Standings
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IEDashboard',
  data () {
    return {
      events: [],
      loading: true,
      error: '',
    }
  },
  computed: {
    tournamentSlug () {
      var cfg = window.ieConfig || {}
      return cfg.tournamentSlug || ''
    },
    pathPrefix () {
      return this.tournamentSlug ? ('/' + this.tournamentSlug) : ''
    },
    setupUrl () {
      return this.pathPrefix + '/admin/ie/setup/'
    },
  },
  mounted () {
    this.fetchEvents()
  },
  methods: {
    apiBase () {
      var cfg = window.ieConfig || {}
      return (window.NEKOSPEECH_URL || cfg.apiBaseUrl || '/api/ie').replace(/\/$/, '')
    },
    async apiFetch (url) {
      var cfg = window.ieConfig || {}
      var headers = {}
      if (cfg.apiKey) headers['X-IE-Api-Key'] = cfg.apiKey

      var response
      try {
        response = await fetch(this.apiBase() + url, { headers: headers })
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
    async fetchEvents () {
      this.loading = true
      this.error = ''
      var cfg = window.ieConfig || {}
      try {
        this.events = await this.apiFetch('/events/?tournament_id=' + cfg.tournamentId)
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    eventLabel (val) {
      var labels = {
        ORATORY: 'Oratory', DI: 'Dramatic Interp', HI: 'Humorous Interp',
        DUO: 'Duo Interp', PROSE: 'Prose', POETRY: 'Poetry', EXTEMP: 'Extemp',
      }
      return labels[val] || val
    },
    availableRounds (ev) {
      var rounds = []
      for (var i = 1; i <= ev.num_rounds; i++) rounds.push(i)
      return rounds
    },
    drawUrl (eventId, round) {
      return this.pathPrefix + '/admin/ie/' + eventId + '/draw/' + round + '/'
    },
    standingsUrl (eventId) {
      return this.pathPrefix + '/admin/ie/' + eventId + '/standings/'
    },
  },
}
</script>
