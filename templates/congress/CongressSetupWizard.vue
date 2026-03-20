<template>
  <div class="card">
    <div class="card-body">
      <h5 class="card-title">Congressional Debate Setup</h5>

      <!-- Step indicators -->
      <div class="d-flex mb-3">
        <span v-for="s in 4" :key="s"
              class="badge mr-2"
              :class="step === s ? 'badge-primary' : 'badge-secondary'">
          Step {{ s }}
        </span>
      </div>

      <!-- Step 1: Tournament configuration -->
      <div v-if="step === 1">
        <label class="form-label font-weight-bold">Tournament Name</label>
        <input v-model="form.name" class="form-control form-control-sm mb-2"
               placeholder="e.g. NSDA District Congress" />
        <div class="row">
          <div class="col-md-3 form-group">
            <label class="font-weight-bold">Prelim Sessions</label>
            <input v-model.number="form.num_preliminary_sessions" type="number"
                   min="1" max="10" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label class="font-weight-bold">Elim Sessions</label>
            <input v-model.number="form.num_elimination_sessions" type="number"
                   min="0" max="5" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label class="font-weight-bold">Chamber Size</label>
            <input v-model.number="form.chamber_size_target" type="number"
                   min="8" max="30" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label class="font-weight-bold">Speech Time (sec)</label>
            <input v-model.number="form.speech_time_seconds" type="number"
                   min="60" class="form-control form-control-sm" />
          </div>
        </div>
        <div class="d-flex justify-content-end">
          <button class="btn btn-primary btn-sm"
                  :disabled="!form.name"
                  @click="step = 2">
            Next →
          </button>
        </div>
      </div>

      <!-- Step 2: Scoring configuration -->
      <div v-if="step === 2">
        <h6 class="font-weight-bold">Scoring Settings</h6>
        <div class="row">
          <div class="col-md-3 form-group">
            <label>Score Min</label>
            <input v-model.number="form.scoring_range_min" type="number"
                   min="0" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label>Score Max</label>
            <input v-model.number="form.scoring_range_max" type="number"
                   min="1" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label>Top N Ranking</label>
            <input v-model.number="form.top_n_ranking" type="number"
                   min="3" max="20" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label>Normalization</label>
            <select v-model="form.normalization_method" class="form-control form-control-sm">
              <option value="ZSCORE">Z-Score</option>
              <option value="PERCENTILE">Percentile</option>
            </select>
          </div>
        </div>
        <h6 class="font-weight-bold mt-2">Penalty Settings</h6>
        <div class="row">
          <div class="col-md-3 form-group">
            <label>Overtime Grace (sec)</label>
            <input v-model.number="form.overtime_grace_seconds" type="number"
                   min="0" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label>Overtime Penalty</label>
            <input v-model.number="form.overtime_penalty_per_interval" type="number"
                   min="0" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label>Wrong Side Penalty</label>
            <input v-model.number="form.wrong_side_penalty" type="number"
                   min="0" class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group">
            <label>Geography Tiebreak</label>
            <select v-model="form.geography_tiebreak_enabled" class="form-control form-control-sm">
              <option :value="false">Disabled</option>
              <option :value="true">Enabled</option>
            </select>
          </div>
        </div>
        <div class="d-flex justify-content-between">
          <button class="btn btn-outline-secondary btn-sm" @click="step = 1">← Back</button>
          <button class="btn btn-primary btn-sm" @click="step = 3">Next →</button>
        </div>
      </div>

      <!-- Step 3: Questioning settings -->
      <div v-if="step === 3">
        <h6 class="font-weight-bold">Questioning Period</h6>
        <div class="row">
          <div class="col-md-4 form-group">
            <label>Question Time (sec)</label>
            <input v-model.number="form.questioning_time_seconds" type="number"
                   min="30" class="form-control form-control-sm" />
          </div>
          <div class="col-md-4 form-group">
            <label>Authorship Q Time (sec)</label>
            <input v-model.number="form.authorship_questioning_time_seconds" type="number"
                   min="30" class="form-control form-control-sm" />
          </div>
          <div class="col-md-4 form-group">
            <label>Direct Questions</label>
            <select v-model="form.direct_questioning_enabled" class="form-control form-control-sm">
              <option :value="true">Enabled</option>
              <option :value="false">Disabled</option>
            </select>
          </div>
        </div>
        <div class="d-flex justify-content-between">
          <button class="btn btn-outline-secondary btn-sm" @click="step = 2">← Back</button>
          <button class="btn btn-primary btn-sm" @click="step = 4">Next →</button>
        </div>
      </div>

      <!-- Step 4: Review & Create -->
      <div v-if="step === 4">
        <h6 class="font-weight-bold">Review Configuration</h6>
        <table class="table table-sm table-bordered mb-3">
          <tbody>
            <tr><th>Name</th><td>{{ form.name }}</td></tr>
            <tr><th>Sessions</th><td>{{ form.num_preliminary_sessions }} prelim + {{ form.num_elimination_sessions }} elim</td></tr>
            <tr><th>Chamber Size</th><td>{{ form.chamber_size_target }}</td></tr>
            <tr><th>Speech Time</th><td>{{ form.speech_time_seconds }}s</td></tr>
            <tr><th>Score Range</th><td>{{ form.scoring_range_min }} – {{ form.scoring_range_max }}</td></tr>
            <tr><th>Normalization</th><td>{{ form.normalization_method }}</td></tr>
          </tbody>
        </table>
        <div v-if="error" class="alert alert-danger alert-sm">{{ error }}</div>
        <div v-if="success" class="alert alert-success alert-sm">Tournament created successfully!</div>
        <div class="d-flex justify-content-between">
          <button class="btn btn-outline-secondary btn-sm" @click="step = 3">← Back</button>
          <button class="btn btn-success btn-sm" :disabled="saving" @click="create">
            {{ saving ? 'Creating…' : 'Create Tournament' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CongressSetupWizard',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      step: 1,
      saving: false,
      error: null,
      success: false,
      form: {
        tournament_id: cfg.tournamentId,
        name: '',
        num_preliminary_sessions: 3,
        num_elimination_sessions: 2,
        chamber_size_target: 18,
        speech_time_seconds: 180,
        authorship_speech_time_seconds: 180,
        scoring_range_min: 1,
        scoring_range_max: 8,
        po_scoring_range_min: 1,
        po_scoring_range_max: 8,
        top_n_ranking: 8,
        normalization_method: 'ZSCORE',
        advancement_method: 'COMBINED',
        overtime_grace_seconds: 10,
        overtime_penalty_per_interval: 1,
        overtime_interval_seconds: 10,
        wrong_side_penalty: 3,
        geography_tiebreak_enabled: false,
        questioning_time_seconds: 60,
        authorship_questioning_time_seconds: 120,
        questioner_segment_seconds: 30,
        direct_questioning_enabled: true,
      },
    }
  },
  methods: {
    async create () {
      this.saving = true
      this.error = null
      try {
        const url = `${this.config.nekocongressUrl}/api/congress/tournaments/`
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Congress-Api-Key': this.config.apiKey,
          },
          body: JSON.stringify(this.form),
        })
        if (!resp.ok) {
          const data = await resp.json()
          throw new Error(data.detail || `HTTP ${resp.status}`)
        }
        this.success = true
      } catch (e) {
        this.error = e.message
      } finally {
        this.saving = false
      }
    },
  },
}
</script>
