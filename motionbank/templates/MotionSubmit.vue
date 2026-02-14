<template>
  <div class="motion-submit">
    <div class="card">
      <div class="card-header"><strong>📝 Submit a Motion</strong></div>
      <div class="card-body">
        <div class="form-group">
          <label>Motion Text <span class="text-danger">*</span></label>
          <textarea v-model="form.text" class="form-control" rows="3"
            placeholder="e.g., This House Would ban all forms of genetic engineering on humans"></textarea>
        </div>

        <div class="row">
          <div class="col-md-4 form-group">
            <label>Format <span class="text-danger">*</span></label>
            <select v-model="form.format" class="form-control">
              <option value="bp">British Parliamentary</option>
              <option value="wsdc">World Schools</option>
              <option value="ap">Asian Parliamentary</option>
              <option value="pf">Public Forum</option>
              <option value="ld">Lincoln-Douglas</option>
              <option value="policy">Policy</option>
            </select>
          </div>
          <div class="col-md-4 form-group">
            <label>Motion Type</label>
            <select v-model="form.motion_type" class="form-control">
              <option value="thw">This House Would</option>
              <option value="thb">This House Believes</option>
              <option value="thbt">This House Believes That</option>
              <option value="thr">This House Regrets</option>
              <option value="policy">Policy</option>
              <option value="value">Value</option>
              <option value="actor">Actor-Specific</option>
            </select>
          </div>
          <div class="col-md-4 form-group">
            <label>Difficulty</label>
            <select v-model="form.difficulty" class="form-control">
              <option value="1">Beginner</option>
              <option value="2">Easy</option>
              <option value="3">Moderate</option>
              <option value="4">Hard</option>
              <option value="5">Expert</option>
            </select>
          </div>
        </div>

        <div class="row">
          <div class="col-md-4 form-group">
            <label>Tournament Name</label>
            <input v-model="form.tournament_name" class="form-control" placeholder="Tournament name" />
          </div>
          <div class="col-md-4 form-group">
            <label>Year</label>
            <input v-model.number="form.year" type="number" class="form-control"
              placeholder="Year" min="1990" max="2030" />
          </div>
          <div class="col-md-4 form-group">
            <label>Region</label>
            <input v-model="form.region" class="form-control" placeholder="e.g., Asia, Europe" />
          </div>
        </div>

        <div class="row">
          <div class="col-md-4 form-group">
            <label>Prep Type</label>
            <select v-model="form.prep_type" class="form-control">
              <option value="impromptu">Impromptu</option>
              <option value="prepared">Prepared</option>
            </select>
          </div>
          <div class="col-md-4 form-group">
            <label>Round Info</label>
            <input v-model="form.round_info" class="form-control" placeholder="e.g., Grand Final, Round 3" />
          </div>
          <div class="col-md-4 form-group">
            <label>Theme Tags (comma-separated)</label>
            <input v-model="themeTagsStr" class="form-control" placeholder="e.g., economics, rights, education" />
          </div>
        </div>

        <div class="form-group">
          <label>Info Slide (optional)</label>
          <textarea v-model="form.info_slide" class="form-control" rows="3"
            placeholder="Background information provided to debaters"></textarea>
        </div>

        <div v-if="error" class="alert alert-danger mt-3">{{ error }}</div>
        <div v-if="success" class="alert alert-success mt-3">{{ success }}</div>

        <div class="d-flex justify-content-between mt-3">
          <a href="/motions-bank/" class="btn btn-outline-secondary">← Back</a>
          <button class="btn btn-primary" @click="submit" :disabled="!canSubmit || submitting">
            {{ submitting ? 'Submitting...' : '🚀 Submit Motion' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MotionSubmit',
  data () {
    return {
      form: {
        text: '',
        format: 'bp',
        motion_type: 'thw',
        difficulty: 3,
        tournament_name: '',
        year: new Date().getFullYear(),
        region: '',
        prep_type: 'impromptu',
        round_info: '',
        info_slide: '',
        theme_tags: [],
      },
      themeTagsStr: '',
      submitting: false,
      error: null,
      success: null,
    }
  },
  computed: {
    canSubmit () {
      return this.form.text.trim().length > 0
    },
  },
  methods: {
    async submit () {
      this.submitting = true
      this.error = null
      this.success = null

      const config = window.motionSubmitConfig || {}
      const csrfToken = this.getCsrf()

      // Parse theme tags
      if (this.themeTagsStr.trim()) {
        this.form.theme_tags = this.themeTagsStr.split(',').map(t => t.trim()).filter(Boolean)
      } else {
        this.form.theme_tags = []
      }

      try {
        const res = await fetch(config.apiUrl || '/motions-bank/api/motions/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(this.form),
        })
        if (res.ok) {
          const data = await res.json()
          this.success = 'Motion submitted successfully! It will appear after review.'
          if (data.slug) {
            setTimeout(() => {
              window.location.href = `/motions-bank/motion/${data.slug}/`
            }, 1500)
          }
        } else {
          const err = await res.json()
          this.error = Object.values(err).flat().join(', ') || 'Failed to submit motion.'
        }
      } catch (e) {
        this.error = 'An error occurred. Please try again.'
      }
      this.submitting = false
    },
    getCsrf () {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || ''
    },
  },
}
</script>
