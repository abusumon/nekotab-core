<template>
  <div>
    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border spinner-border-sm mr-1"></span> Loading events...
    </div>

    <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

    <div v-else-if="events.length === 0" class="alert alert-secondary">
      No events are available yet.
    </div>

    <div v-else>
      <div v-for="ev in events" :key="ev.id" class="card mb-3">
        <div class="card-body">
          <h5 class="card-title mb-1">
            {{ ev.name }}
            <small class="text-muted">({{ ev.abbreviation }})</small>
          </h5>
          <p class="text-muted small mb-2">
            {{ eventLabel(ev.event_type) }} · {{ ev.num_rounds }} rounds · {{ ev.entry_count }} entries
          </p>
          <div class="d-flex flex-wrap">
            <a :href="standingsUrl(ev.id)"
               class="btn btn-outline-primary btn-sm mr-2 mb-1">
              View Standings
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IEPublicLanding',
  data () {
    return {
      events: [],
      loading: true,
      error: '',
    }
  },
  computed: {
    pathPrefix () {
      var cfg = window.ieConfig || {}
      return cfg.tournamentSlug ? ('/' + cfg.tournamentSlug) : ''
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
        ORATORY: 'Oratory', DI: 'Dramatic Interpretation', HI: 'Humorous Interpretation',
        DUO: 'Duo Interpretation', PROSE: 'Prose', POETRY: 'Poetry', EXTEMP: 'Extemporaneous Speaking',
      }
      return labels[val] || val
    },
    standingsUrl (eventId) {
      return this.pathPrefix + '/ie/' + eventId + '/standings/'
    },
  },
}
</script>
