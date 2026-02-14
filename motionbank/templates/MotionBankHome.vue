<template>
  <div class="motion-bank">
    <!-- Hero / Search Section -->
    <div class="card mb-4 bg-primary text-white">
      <div class="card-body py-4">
        <h2 class="mb-2">🌐 Global Motion Bank</h2>
        <p class="mb-3">Browse thousands of debate motions from tournaments worldwide</p>
        <div class="row">
          <div class="col-md-8">
            <input v-model="searchQuery" type="text" class="form-control form-control-lg"
              placeholder="Search motions by text, theme, or tournament..."
              @input="debounceSearch" />
          </div>
          <div class="col-md-4 mt-2 mt-md-0">
            <a href="/motions-bank/doctor/" class="btn btn-light btn-lg btn-block">
              🩺 Motion Doctor
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="card mb-3">
      <div class="card-body py-2">
        <div class="row">
          <div class="col-md-2 mb-2">
            <select v-model="filters.format" class="form-control form-control-sm" @change="fetchMotions">
              <option value="">All Formats</option>
              <option value="bp">British Parliamentary</option>
              <option value="wsdc">World Schools</option>
              <option value="ap">Australs / Asian Parliamentary</option>
              <option value="pf">Public Forum</option>
              <option value="ld">Lincoln-Douglas</option>
              <option value="policy">Policy</option>
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <select v-model="filters.difficulty" class="form-control form-control-sm" @change="fetchMotions">
              <option value="">All Difficulties</option>
              <option value="1">Beginner</option>
              <option value="2">Easy</option>
              <option value="3">Moderate</option>
              <option value="4">Hard</option>
              <option value="5">Expert</option>
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <select v-model="filters.type" class="form-control form-control-sm" @change="fetchMotions">
              <option value="">All Types</option>
              <option value="thw">This House Would</option>
              <option value="thb">This House Believes</option>
              <option value="thbt">This House Believes That</option>
              <option value="thr">This House Regrets</option>
              <option value="policy">Policy</option>
              <option value="value">Value</option>
              <option value="actor">Actor-Specific</option>
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <input v-model="filters.year" type="number" class="form-control form-control-sm"
              placeholder="Year" min="1990" max="2030" @change="fetchMotions" />
          </div>
          <div class="col-md-2 mb-2">
            <input v-model="filters.region" type="text" class="form-control form-control-sm"
              placeholder="Region" @input="debounceSearch" />
          </div>
          <div class="col-md-2 mb-2">
            <select v-model="filters.prep" class="form-control form-control-sm" @change="fetchMotions">
              <option value="">Prepared & Impromptu</option>
              <option value="prepared">Prepared</option>
              <option value="impromptu">Impromptu</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Results -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"><span class="sr-only">Loading...</span></div>
    </div>

    <div v-else>
      <div v-for="motion in motions" :key="motion.id" class="card mb-2 motion-card">
        <div class="card-body py-3">
          <a :href="'/motions-bank/motion/' + motion.slug + '/'" class="text-dark text-decoration-none">
            <h6 class="mb-2">{{ motion.text }}</h6>
          </a>
          <div class="d-flex flex-wrap align-items-center" style="gap: 6px;">
            <span class="badge badge-primary">{{ motion.format_display }}</span>
            <span class="badge badge-secondary">{{ motion.type_display }}</span>
            <span class="badge" :class="difficultyClass(motion.difficulty)">
              {{ motion.difficulty_display }}
            </span>
            <span v-if="motion.tournament_name" class="badge badge-dark">{{ motion.tournament_name }}</span>
            <span v-if="motion.year" class="badge badge-outline-secondary">{{ motion.year }}</span>
            <span v-if="motion.region" class="badge badge-outline-info">{{ motion.region }}</span>
            <span v-for="tag in (motion.theme_tags || [])" :key="tag"
              class="badge badge-outline-primary">{{ tag }}</span>
            <span v-if="motion.has_analysis" class="badge badge-success ml-auto">🤖 AI Analyzed</span>
            <span v-if="motion.stats" class="text-muted small ml-2">
              ⭐ {{ (motion.stats.average_rating || 0).toFixed(1) }}
              · 📝 {{ motion.stats.times_practiced || 0 }} practiced
            </span>
          </div>
        </div>
      </div>

      <div v-if="motions.length === 0" class="card">
        <div class="card-body text-center py-5">
          <h5 class="text-muted">No motions found</h5>
          <p class="text-muted">Try adjusting your filters.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MotionBankHome',
  data () {
    return {
      motions: [],
      loading: true,
      searchQuery: '',
      searchTimeout: null,
      filters: {
        format: '',
        difficulty: '',
        type: '',
        year: '',
        region: '',
        prep: '',
      },
    }
  },
  mounted () {
    this.fetchMotions()
  },
  methods: {
    async fetchMotions () {
      this.loading = true
      try {
        const params = new URLSearchParams()
        if (this.searchQuery) params.set('search', this.searchQuery)
        Object.entries(this.filters).forEach(([k, v]) => {
          if (v) params.set(k, v)
        })
        const url = `${(window.motionBankConfig || {}).apiBase || '/motions-bank/api/motions/'}?${params}`
        const response = await fetch(url)
        const data = await response.json()
        this.motions = data.results || data
      } catch (e) {
        console.error('Failed to fetch motions:', e)
      }
      this.loading = false
    },
    debounceSearch () {
      clearTimeout(this.searchTimeout)
      this.searchTimeout = setTimeout(() => this.fetchMotions(), 300)
    },
    difficultyClass (level) {
      const map = { 1: 'badge-success', 2: 'badge-info', 3: 'badge-warning', 4: 'badge-danger', 5: 'badge-dark' }
      return map[level] || 'badge-secondary'
    },
  },
}
</script>
