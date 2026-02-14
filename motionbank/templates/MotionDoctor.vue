<template>
  <div class="motion-doctor">
    <div class="card mb-4">
      <div class="card-body">
        <h3 class="mb-3">🩺 Motion Doctor</h3>
        <p class="text-muted">Paste any debate motion for instant AI-powered analysis.</p>

        <div class="form-group">
          <textarea v-model="motionText" class="form-control" rows="3"
            placeholder="e.g., This House Would ban all forms of genetic engineering on humans"
            :disabled="analyzing"></textarea>
        </div>

        <div class="row mb-3">
          <div class="col-md-4">
            <select v-model="format" class="form-control">
              <option value="">Select format (optional)</option>
              <option value="bp">British Parliamentary</option>
              <option value="wsdc">World Schools</option>
              <option value="ap">Australs / Asian Parliamentary</option>
              <option value="pf">Public Forum</option>
            </select>
          </div>
          <div class="col-md-4">
            <input v-model="infoSlide" type="text" class="form-control"
              placeholder="Info slide (optional)" />
          </div>
          <div class="col-md-4">
            <button class="btn btn-primary btn-block" @click="analyze"
              :disabled="!motionText.trim() || analyzing">
              {{ analyzing ? 'Analyzing...' : '🔍 Analyze Motion' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Analysis Results -->
    <div v-if="analysis" class="analysis-results">
      <!-- Clash Areas -->
      <div class="card mb-3">
        <div class="card-header bg-primary text-white"><strong>⚔️ Clash Areas</strong></div>
        <div class="card-body">
          <ul class="mb-0">
            <li v-for="(clash, i) in analysis.clash_areas" :key="'clash-'+i">{{ clash }}</li>
          </ul>
        </div>
      </div>

      <!-- Hidden Assumptions -->
      <div class="card mb-3">
        <div class="card-header"><strong>🔍 Hidden Assumptions</strong></div>
        <div class="card-body">
          <ul class="mb-0">
            <li v-for="(a, i) in analysis.hidden_assumptions" :key="'ha-'+i">{{ a }}</li>
          </ul>
        </div>
      </div>

      <!-- Definition Traps -->
      <div class="card mb-3">
        <div class="card-header"><strong>⚠️ Definition Traps</strong></div>
        <div class="card-body">
          <ul class="mb-0">
            <li v-for="(d, i) in analysis.definition_traps" :key="'dt-'+i">{{ d }}</li>
          </ul>
        </div>
      </div>

      <!-- Gov & Opp Approaches -->
      <div class="row mb-3">
        <div class="col-md-6">
          <div class="card h-100 border-success">
            <div class="card-header bg-success text-white"><strong>🟢 Gov / Prop Approach</strong></div>
            <div class="card-body" v-if="analysis.gov_approach">
              <p><strong>Structure:</strong> {{ analysis.gov_approach.structure }}</p>
              <p><strong>Key Arguments:</strong></p>
              <ul>
                <li v-for="(arg, i) in analysis.gov_approach.key_args" :key="'ga-'+i">{{ arg }}</li>
              </ul>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card h-100 border-danger">
            <div class="card-header bg-danger text-white"><strong>🔴 Opp Approach</strong></div>
            <div class="card-body" v-if="analysis.opp_approach">
              <p><strong>Structure:</strong> {{ analysis.opp_approach.structure }}</p>
              <p><strong>Key Arguments:</strong></p>
              <ul>
                <li v-for="(arg, i) in analysis.opp_approach.key_args" :key="'oa-'+i">{{ arg }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Burden Split -->
      <div v-if="analysis.burden_split" class="card mb-3">
        <div class="card-header"><strong>⚖️ Burden Split</strong></div>
        <div class="card-body">{{ analysis.burden_split }}</div>
      </div>

      <!-- Likely Extensions (BP) -->
      <div v-if="analysis.likely_extensions" class="card mb-3">
        <div class="card-header"><strong>🔗 Likely Extensions (BP)</strong></div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-3" v-for="(ext, role) in analysis.likely_extensions" :key="role">
              <strong>{{ role }}:</strong>
              <p>{{ ext }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Weighing Options -->
      <div v-if="analysis.weighing_options" class="card mb-3">
        <div class="card-header"><strong>📊 Weighing Options</strong></div>
        <div class="card-body">
          <ul class="mb-0">
            <li v-for="(w, i) in analysis.weighing_options" :key="'wo-'+i">{{ w }}</li>
          </ul>
        </div>
      </div>

      <!-- Suggested POIs -->
      <div v-if="analysis.suggested_pois" class="card mb-3">
        <div class="card-header"><strong>❓ 10 Suggested POIs</strong></div>
        <div class="card-body">
          <ol class="mb-0">
            <li v-for="(poi, i) in analysis.suggested_pois" :key="'poi-'+i">{{ poi }}</li>
          </ol>
        </div>
      </div>

      <!-- Common Framing Mistakes -->
      <div v-if="analysis.framing_mistakes" class="card mb-3">
        <div class="card-header"><strong>🚫 Common Framing Mistakes</strong></div>
        <div class="card-body">
          <ul class="mb-0">
            <li v-for="(m, i) in analysis.framing_mistakes" :key="'fm-'+i">{{ m }}</li>
          </ul>
        </div>
      </div>

      <!-- Model Problems -->
      <div v-if="analysis.model_problems" class="card mb-3">
        <div class="card-header"><strong>🔧 Likely Model Problems</strong></div>
        <div class="card-body">
          <ul class="mb-0">
            <li v-for="(p, i) in analysis.model_problems" :key="'mp-'+i">{{ p }}</li>
          </ul>
        </div>
      </div>

      <!-- Difficulty -->
      <div v-if="analysis.difficulty_rationale" class="card mb-3">
        <div class="card-header"><strong>📈 Difficulty Assessment</strong></div>
        <div class="card-body">{{ analysis.difficulty_rationale }}</div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'MotionDoctor',
  data () {
    return {
      motionText: '',
      format: '',
      infoSlide: '',
      analysis: null,
      analyzing: false,
      error: null,
    }
  },
  methods: {
    async analyze () {
      this.analyzing = true
      this.error = null
      this.analysis = null
      try {
        const config = window.motionDoctorConfig || {}
        const url = config.analyzeUrl || '/motions-bank/api/doctor/analyze/'
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
          document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1]

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            motion_text: this.motionText,
            format: this.format || undefined,
            info_slide: this.infoSlide || undefined,
          }),
        })
        if (!response.ok) throw new Error('Analysis failed')
        const data = await response.json()
        this.analysis = data.analysis || data
      } catch (e) {
        this.error = 'Failed to analyze motion. Please try again.'
        console.error(e)
      }
      this.analyzing = false
    },
  },
}
</script>
