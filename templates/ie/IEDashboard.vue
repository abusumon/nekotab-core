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
      <!-- Event Cards -->
      <div v-for="ev in events" :key="ev.id" class="card mb-3">
        <div class="card-body">
          <!-- Event Header -->
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <h5 class="card-title mb-1">
                {{ ev.name }}
                <small class="text-muted">({{ ev.abbreviation }})</small>
              </h5>
              <p class="text-muted small mb-2">
                {{ ev.num_rounds }} rounds · Room size {{ ev.room_size }} · {{ ev.tiebreak_method }} tiebreak
              </p>
            </div>
            <div>
              <button class="btn btn-outline-secondary btn-sm mr-1"
                      @click="toggleEdit(ev)">
                {{ editingId === ev.id ? 'Cancel' : 'Edit' }}
              </button>
              <button class="btn btn-outline-danger btn-sm"
                      @click="toggleDeactivate(ev)">
                {{ deactivatingId === ev.id ? 'Cancel' : 'Deactivate' }}
              </button>
            </div>
          </div>

          <!-- Inline Edit Panel -->
          <div v-if="editingId === ev.id" class="border rounded p-3 mb-3 bg-light">
            <div class="row">
              <div class="col-md-4 form-group mb-2">
                <label class="font-weight-bold small">Name</label>
                <input v-model="editForm.name" class="form-control form-control-sm" />
              </div>
              <div class="col-md-2 form-group mb-2">
                <label class="font-weight-bold small">Abbreviation</label>
                <input v-model="editForm.abbreviation" class="form-control form-control-sm" maxlength="20" />
              </div>
              <div class="col-md-2 form-group mb-2">
                <label class="font-weight-bold small">Rounds</label>
                <input v-model.number="editForm.num_rounds" type="number" min="1" class="form-control form-control-sm" />
              </div>
              <div class="col-md-2 form-group mb-2">
                <label class="font-weight-bold small">Room Size</label>
                <input v-model.number="editForm.room_size" type="number" min="2" max="12" class="form-control form-control-sm" />
              </div>
              <div class="col-md-2 form-group mb-2">
                <label class="font-weight-bold small">Tiebreak</label>
                <select v-model="editForm.tiebreak_method" class="form-control form-control-sm">
                  <option value="TRUNC">Truncated Rank</option>
                  <option value="LOW">Lowest Rank Sum</option>
                </select>
              </div>
            </div>
            <div v-if="editError" class="alert alert-danger py-1 small">{{ editError }}</div>
            <button class="btn btn-primary btn-sm" :disabled="saving" @click="saveEdit(ev)">
              <span v-if="saving" class="spinner-border spinner-border-sm mr-1"></span>
              Save Changes
            </button>
          </div>

          <!-- Inline Deactivate Confirmation -->
          <div v-if="deactivatingId === ev.id" class="alert alert-warning py-2 mb-3">
            <strong>Deactivate "{{ ev.name }}"?</strong>
            <span v-if="ev.entry_count > 0"> This event has {{ ev.entry_count }} entries.</span>
            All draw data will be hidden.
            <button class="btn btn-danger btn-sm ml-2" :disabled="deleting" @click="deactivateEvent(ev)">
              <span v-if="deleting" class="spinner-border spinner-border-sm mr-1"></span>
              Deactivate
            </button>
          </div>

          <!-- Status Row -->
          <div class="d-flex align-items-center flex-wrap mb-2">
            <span class="mr-3">
              <strong>{{ ev.entry_count }}</strong> entries
            </span>
            <span class="mr-1 small text-muted">Rounds:</span>
            <span v-for="rd in ev.num_rounds" :key="rd" class="mr-1">
              <span class="badge" :class="roundBadgeClass(ev, rd)"
                    :title="roundTooltip(ev, rd)">
                R{{ rd }} {{ roundIcon(ev, rd) }}
              </span>
            </span>
          </div>

          <!-- Action Buttons -->
          <div class="d-flex flex-wrap">
            <a :href="entriesUrl(ev.id)"
               class="btn btn-outline-primary btn-sm mr-1 mb-1">
              Entries ({{ ev.entry_count }})
            </a>
            <a v-for="rd in ev.num_rounds" :key="'draw-' + rd"
               :href="drawUrl(ev.id, rd)"
               class="btn btn-sm mr-1 mb-1"
               :class="drawBtnClass(ev, rd)">
              Draw R{{ rd }}
            </a>
            <a :href="standingsUrl(ev.id)"
               class="btn btn-outline-info btn-sm mr-1 mb-1">
              Standings
            </a>
            <a v-if="allPrelimsConfirmed(ev)"
               :href="finalistsUrl(ev.id)"
               class="btn btn-outline-success btn-sm mr-1 mb-1">
              Finals
            </a>
          </div>
        </div>
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
      editingId: null,
      deactivatingId: null,
      editForm: {},
      editError: '',
      saving: false,
      deleting: false,
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

      if (response.status === 204) return null
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
    // Round status helpers
    roundStatus (ev, rd) {
      if (!ev.rounds_with_draw || ev.rounds_with_draw.indexOf(rd) === -1) return 'none'
      if (ev.confirmed_rounds && ev.confirmed_rounds.indexOf(rd) !== -1) return 'confirmed'
      return 'pending'
    },
    roundIcon (ev, rd) {
      var s = this.roundStatus(ev, rd)
      if (s === 'confirmed') return '✓'
      if (s === 'pending') return '⏳'
      return '○'
    },
    roundBadgeClass (ev, rd) {
      var s = this.roundStatus(ev, rd)
      if (s === 'confirmed') return 'badge-success'
      if (s === 'pending') return 'badge-warning'
      return 'badge-light'
    },
    roundTooltip (ev, rd) {
      var s = this.roundStatus(ev, rd)
      if (s === 'confirmed') return 'Round ' + rd + ': all rooms confirmed'
      if (s === 'pending') return 'Round ' + rd + ': draw generated, ballots pending'
      return 'Round ' + rd + ': not started'
    },
    drawBtnClass (ev, rd) {
      var s = this.roundStatus(ev, rd)
      if (s === 'confirmed') return 'btn-outline-success'
      if (s === 'pending') return 'btn-warning'
      return 'btn-outline-secondary'
    },
    allPrelimsConfirmed (ev) {
      if (!ev.confirmed_rounds) return false
      for (var r = 1; r <= ev.num_rounds; r++) {
        if (ev.confirmed_rounds.indexOf(r) === -1) return false
      }
      return true
    },
    // URL helpers
    entriesUrl (eventId) {
      return this.pathPrefix + '/admin/ie/' + eventId + '/entries/'
    },
    drawUrl (eventId, round) {
      return this.pathPrefix + '/admin/ie/' + eventId + '/draw/' + round + '/'
    },
    standingsUrl (eventId) {
      return this.pathPrefix + '/admin/ie/' + eventId + '/standings/'
    },
    finalistsUrl (eventId) {
      return this.pathPrefix + '/admin/ie/' + eventId + '/finalists/'
    },
    // Edit
    toggleEdit (ev) {
      if (this.editingId === ev.id) {
        this.editingId = null
        return
      }
      this.editingId = ev.id
      this.deactivatingId = null
      this.editError = ''
      this.editForm = {
        name: ev.name,
        abbreviation: ev.abbreviation,
        num_rounds: ev.num_rounds,
        room_size: ev.room_size,
        tiebreak_method: ev.tiebreak_method,
      }
    },
    async saveEdit (ev) {
      this.saving = true
      this.editError = ''
      try {
        var updated = await this.apiFetch('/events/' + ev.id + '/', {
          method: 'PATCH',
          body: JSON.stringify(this.editForm),
        })
        // Update local event data
        ev.name = updated.name
        ev.abbreviation = updated.abbreviation
        ev.num_rounds = updated.num_rounds
        ev.room_size = updated.room_size
        ev.tiebreak_method = updated.tiebreak_method
        this.editingId = null
      } catch (e) {
        this.editError = e.message
      } finally {
        this.saving = false
      }
    },
    // Deactivate
    toggleDeactivate (ev) {
      if (this.deactivatingId === ev.id) {
        this.deactivatingId = null
        return
      }
      this.deactivatingId = ev.id
      this.editingId = null
    },
    async deactivateEvent (ev) {
      this.deleting = true
      try {
        await this.apiFetch('/events/' + ev.id + '/', { method: 'DELETE' })
        this.events = this.events.filter(function (e) { return e.id !== ev.id })
        this.deactivatingId = null
      } catch (e) {
        this.error = e.message
      } finally {
        this.deleting = false
      }
    },
  },
}
</script>
