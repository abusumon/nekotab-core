<template>
  <div class="passport-edit">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"><span class="sr-only">Loading...</span></div>
    </div>

    <div v-else>
      <div class="card">
        <div class="card-header">
          <strong>{{ isNew ? '🆕 Create Your Debate Passport' : '✏️ Edit Your Passport' }}</strong>
        </div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-6 form-group">
              <label>Display Name</label>
              <input v-model="form.display_name" class="form-control" placeholder="Your public name" />
            </div>
            <div class="col-md-6 form-group">
              <label>Institution</label>
              <input v-model="form.institution" class="form-control" placeholder="University / School" />
            </div>
          </div>

          <div class="row">
            <div class="col-md-4 form-group">
              <label>Country</label>
              <input v-model="form.country" class="form-control" placeholder="Country" />
            </div>
            <div class="col-md-4 form-group">
              <label>Country Code</label>
              <input v-model="form.country_code" class="form-control" placeholder="e.g., US, GB, BD" maxlength="2" />
            </div>
            <div class="col-md-4 form-group">
              <label>Primary Format</label>
              <select v-model="form.primary_format" class="form-control">
                <option value="bp">British Parliamentary</option>
                <option value="wsdc">World Schools</option>
                <option value="ap">Asian Parliamentary</option>
                <option value="pf">Public Forum</option>
                <option value="ld">Lincoln-Douglas</option>
                <option value="policy">Policy</option>
                <option value="cp">Canadian Parliamentary</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div class="row">
            <div class="col-md-4 form-group">
              <label>Experience Level</label>
              <select v-model="form.experience_level" class="form-control">
                <option value="novice">Novice</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
                <option value="expert">Expert</option>
              </select>
            </div>
            <div class="col-md-8 form-group">
              <label>Bio</label>
              <textarea v-model="form.bio" class="form-control" rows="3"
                placeholder="Tell others about your debate journey..."></textarea>
            </div>
          </div>

          <div class="form-group">
            <label class="d-block mb-2">Roles</label>
            <div class="form-check form-check-inline">
              <input v-model="form.is_speaker" type="checkbox" class="form-check-input" id="role-speaker">
              <label class="form-check-label" for="role-speaker">🎤 Speaker</label>
            </div>
            <div class="form-check form-check-inline">
              <input v-model="form.is_judge" type="checkbox" class="form-check-input" id="role-judge">
              <label class="form-check-label" for="role-judge">⚖️ Judge</label>
            </div>
            <div class="form-check form-check-inline">
              <input v-model="form.is_ca" type="checkbox" class="form-check-input" id="role-ca">
              <label class="form-check-label" for="role-ca">👑 CA</label>
            </div>
            <div class="form-check form-check-inline">
              <input v-model="form.is_coach" type="checkbox" class="form-check-input" id="role-coach">
              <label class="form-check-label" for="role-coach">📋 Coach</label>
            </div>
          </div>

          <hr>
          <h5 class="mb-3">Privacy Settings</h5>
          <div class="row">
            <div class="col-md-4 form-group">
              <div class="form-check">
                <input v-model="form.is_public" type="checkbox" class="form-check-input" id="privacy-public">
                <label class="form-check-label" for="privacy-public">Public Profile</label>
              </div>
            </div>
            <div class="col-md-4 form-group">
              <div class="form-check">
                <input v-model="form.show_stats" type="checkbox" class="form-check-input" id="privacy-stats">
                <label class="form-check-label" for="privacy-stats">Show Statistics</label>
              </div>
            </div>
            <div class="col-md-4 form-group">
              <div class="form-check">
                <input v-model="form.show_history" type="checkbox" class="form-check-input" id="privacy-history">
                <label class="form-check-label" for="privacy-history">Show Tournament History</label>
              </div>
            </div>
          </div>

          <div v-if="error" class="alert alert-danger mt-3">{{ error }}</div>
          <div v-if="success" class="alert alert-success mt-3">{{ success }}</div>

          <div class="d-flex justify-content-between mt-3">
            <a href="/passport/" class="btn btn-outline-secondary">← Back</a>
            <div>
              <a href="/passport/dashboard/" class="btn btn-outline-primary mr-2">📊 Dashboard</a>
              <button class="btn btn-primary" @click="save" :disabled="saving">
                {{ saving ? 'Saving...' : '💾 Save Passport' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PassportEdit',
  data () {
    return {
      form: {
        display_name: '',
        institution: '',
        country: '',
        country_code: '',
        primary_format: 'bp',
        experience_level: 'novice',
        bio: '',
        is_speaker: true,
        is_judge: false,
        is_ca: false,
        is_coach: false,
        is_public: true,
        show_stats: true,
        show_history: true,
      },
      loading: true,
      saving: false,
      isNew: true,
      error: null,
      success: null,
    }
  },
  mounted () {
    this.fetchPassport()
  },
  methods: {
    async fetchPassport () {
      const config = window.passportEditConfig || {}
      try {
        const res = await fetch(config.apiUrl || '/passport/api/passports/me/')
        if (res.ok) {
          const data = await res.json()
          this.isNew = false
          Object.keys(this.form).forEach(key => {
            if (data[key] !== undefined) this.form[key] = data[key]
          })
        }
      } catch (e) { console.error(e) }
      this.loading = false
    },
    async save () {
      this.saving = true
      this.error = null
      this.success = null
      const config = window.passportEditConfig || {}
      const csrfToken = this.getCsrf()

      try {
        const res = await fetch(config.apiUrl || '/passport/api/passports/me/', {
          method: this.isNew ? 'POST' : 'PATCH',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(this.form),
        })
        if (res.ok) {
          this.success = 'Passport saved successfully!'
          this.isNew = false
        } else {
          const err = await res.json()
          this.error = Object.values(err).flat().join(', ') || 'Failed to save.'
        }
      } catch (e) {
        this.error = 'An error occurred. Please try again.'
      }
      this.saving = false
    },
    getCsrf () {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || ''
    },
  },
}
</script>
