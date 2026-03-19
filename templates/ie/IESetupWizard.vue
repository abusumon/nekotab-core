<template>
  <div class="card">
    <div class="card-body">
      <h5 class="card-title">Create Individual Event</h5>

      <!-- Step indicators -->
      <div class="d-flex mb-3">
        <span v-for="s in 3" :key="s"
              class="badge mr-2"
              :class="step === s ? 'badge-primary' : 'badge-secondary'">
          Step {{ s }}
        </span>
      </div>

      <!-- Step 1: Select event type -->
      <div v-if="step === 1">
        <label class="form-label font-weight-bold">Event Type</label>
        <select v-model="form.event_type" class="form-control form-control-sm mb-3">
          <option value="">— Select —</option>
          <option v-for="et in eventTypes" :key="et.value" :value="et.value">
            {{ et.label }}
          </option>
        </select>
        <div class="d-flex justify-content-end">
          <button class="btn btn-primary btn-sm"
                  :disabled="!form.event_type"
                  @click="step = 2">
            Next →
          </button>
        </div>
      </div>

      <!-- Step 2: Configure -->
      <div v-if="step === 2">
        <div class="form-group">
          <label class="font-weight-bold">Event Name</label>
          <input v-model="form.name" class="form-control form-control-sm"
                 placeholder="e.g. Varsity Oratory" />
        </div>
        <div class="form-group">
          <label class="font-weight-bold">Abbreviation</label>
          <input v-model="form.abbreviation" class="form-control form-control-sm"
                 placeholder="e.g. ORA" maxlength="20" />
        </div>
        <div class="row">
          <div class="col-md-4 form-group">
            <label class="font-weight-bold">Rounds</label>
            <input v-model.number="form.num_rounds" type="number" min="1"
                   class="form-control form-control-sm" />
          </div>
          <div class="col-md-4 form-group">
            <label class="font-weight-bold">Room Size</label>
            <input v-model.number="form.room_size" type="number" min="2" max="12"
                   class="form-control form-control-sm" />
          </div>
          <div class="col-md-4 form-group">
            <label class="font-weight-bold">Tiebreak</label>
            <select v-model="form.tiebreak_method" class="form-control form-control-sm">
              <option value="TRUNC">Truncated Rank</option>
              <option value="LOW">Lowest Rank Sum</option>
            </select>
          </div>
        </div>
        <div class="d-flex justify-content-between">
          <button class="btn btn-outline-secondary btn-sm" @click="step = 1">← Back</button>
          <button class="btn btn-primary btn-sm"
                  :disabled="!form.name || !form.abbreviation"
                  @click="step = 3">
            Next →
          </button>
        </div>
      </div>

      <!-- Step 3: Confirm -->
      <div v-if="step === 3">
        <table class="table table-sm table-bordered mb-3">
          <tbody>
            <tr><th>Event Type</th><td>{{ eventLabel(form.event_type) }}</td></tr>
            <tr><th>Name</th><td>{{ form.name }}</td></tr>
            <tr><th>Abbreviation</th><td>{{ form.abbreviation }}</td></tr>
            <tr><th>Rounds</th><td>{{ form.num_rounds }}</td></tr>
            <tr><th>Room Size</th><td>{{ form.room_size }}</td></tr>
            <tr><th>Tiebreak</th><td>{{ form.tiebreak_method }}</td></tr>
          </tbody>
        </table>
        <div v-if="error && !submitting" class="alert alert-danger">{{ error }}</div>
        <div class="d-flex justify-content-between">
          <button v-if="!submitting" class="btn btn-outline-secondary btn-sm" @click="step = 2">← Back</button>
          <span v-else></span>
          <button class="btn btn-success btn-sm" :disabled="submitting" @click="createEvent">
            <span v-if="submitting" class="spinner-border spinner-border-sm mr-1"></span>
            {{ submitting ? 'Creating...' : 'Create Event' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IESetupWizard',
  data () {
    return {
      step: 1,
      submitting: false,
      error: '',
      form: {
        tournament_id: window.ieConfig ? window.ieConfig.tournamentId : null,
        event_type: '',
        name: '',
        abbreviation: '',
        num_rounds: 3,
        room_size: 6,
        tiebreak_method: 'TRUNC',
      },
      eventTypes: [
        { value: 'ORATORY', label: 'Oratory' },
        { value: 'DI', label: 'Dramatic Interpretation' },
        { value: 'HI', label: 'Humorous Interpretation' },
        { value: 'DUO', label: 'Duo Interpretation' },
        { value: 'PROSE', label: 'Prose' },
        { value: 'POETRY', label: 'Poetry' },
        { value: 'EXTEMP', label: 'Extemporaneous Speaking' },
      ],
    }
  },
  methods: {
    apiBase () {
      var cfg = window.ieConfig || {}
      return (window.NEKOSPEECH_URL || cfg.apiBaseUrl || '/api/ie').replace(/\/$/, '')
    },
    apiHeaders () {
      var cfg = window.ieConfig || {}
      var headers = { 'Content-Type': 'application/json' }
      if (cfg.apiKey) headers['X-IE-Api-Key'] = cfg.apiKey
      return headers
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
    eventLabel (val) {
      var et = this.eventTypes.find(function (e) { return e.value === val })
      return et ? et.label : val
    },
    async createEvent () {
      this.submitting = true
      this.error = ''
      try {
        await this.apiFetch('/events/', {
          method: 'POST',
          body: JSON.stringify(this.form),
        })
        // Success — redirect to IE dashboard
        var cfg = window.ieConfig || {}
        var slug = cfg.tournamentSlug || ''
        window.location.href = slug ? ('/' + slug + '/admin/ie/') : '/admin/ie/'
      } catch (e) {
        this.error = e.message
        // Stay on Step 3 — do not reset
      } finally {
        this.submitting = false
      }
    },
  },
}
</script>
