<template>
  <div class="passport-directory">
    <!-- Search & Filters -->
    <div class="card mb-3">
      <div class="card-body">
        <div class="row">
          <div class="col-md-4 mb-2">
            <input v-model="searchQuery" type="text" class="form-control"
              placeholder="Search debaters by name, institution, country..."
              @input="debounceSearch" />
          </div>
          <div class="col-md-2 mb-2">
            <select v-model="filters.format" class="form-control" @change="fetchPassports">
              <option value="">All Formats</option>
              <option value="bp">British Parliamentary</option>
              <option value="wsdc">World Schools</option>
              <option value="ap">Asian Parliamentary</option>
              <option value="pf">Public Forum</option>
              <option value="ld">Lincoln-Douglas</option>
              <option value="policy">Policy</option>
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <select v-model="filters.level" class="form-control" @change="fetchPassports">
              <option value="">All Levels</option>
              <option value="novice">Novice</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
              <option value="expert">Expert</option>
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <select v-model="activeTab" class="form-control">
              <option value="directory">Directory</option>
              <option value="leaderboard">Leaderboard</option>
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <a v-if="config.isAuthenticated" href="/passport/edit/" class="btn btn-primary btn-block">
              My Passport
            </a>
            <a v-else href="/accounts/login/" class="btn btn-outline-primary btn-block">Login</a>
          </div>
        </div>
      </div>
    </div>

    <!-- Directory View -->
    <div v-if="activeTab === 'directory'">
      <div v-if="loading" class="text-center py-5">
        <div class="spinner-border text-primary"><span class="sr-only">Loading...</span></div>
      </div>

      <div v-else>
        <div v-for="passport in passports" :key="passport.id" class="card mb-2">
          <div class="card-body py-3">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <a :href="'/passport/profile/' + passport.user_id + '/'" class="h6 mb-0 text-dark text-decoration-none">
                  {{ passport.display_name }}
                </a>
                <div class="text-muted small mt-1">
                  <span v-if="passport.country" class="mr-2">🌍 {{ passport.country }}</span>
                  <span v-if="passport.institution" class="mr-2">🏫 {{ passport.institution }}</span>
                  <span class="badge badge-outline-primary mr-1">{{ passport.experience_level_display }}</span>
                  <span class="badge badge-outline-secondary">{{ passport.primary_format_display }}</span>
                </div>
                <div class="mt-1">
                  <span v-if="passport.is_speaker" class="badge badge-primary badge-sm mr-1">Speaker</span>
                  <span v-if="passport.is_judge" class="badge badge-info badge-sm mr-1">Judge</span>
                  <span v-if="passport.is_ca" class="badge badge-warning badge-sm mr-1">CA</span>
                </div>
              </div>
              <div class="text-right text-muted small">
                <div v-if="passport.stats">🏆 {{ passport.stats.total_tournaments || 0 }} tournaments</div>
                <div v-if="passport.stats && passport.stats.average_speaker_score">⭐ {{ passport.stats.average_speaker_score.toFixed(1) }}</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="passports.length === 0" class="card">
          <div class="card-body text-center py-5">
            <h5 class="text-muted">No passports found</h5>
            <p class="text-muted">Try adjusting your search or filters.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Leaderboard View -->
    <div v-if="activeTab === 'leaderboard'">
      <div class="row">
        <div class="col-md-6 mb-4">
          <div class="card h-100">
            <div class="card-header"><strong>🎤 Top Speakers</strong></div>
            <div class="list-group list-group-flush">
              <div v-for="(entry, idx) in leaderboard.speakers || []" :key="'s-'+idx"
                class="list-group-item d-flex justify-content-between">
                <span>
                  <strong class="mr-2">#{{ idx + 1 }}</strong>
                  <a :href="'/passport/profile/' + entry.user_id + '/'" class="text-dark">
                    {{ entry.display_name }}
                  </a>
                </span>
                <span class="text-muted">{{ entry.average_speaker_score ? entry.average_speaker_score.toFixed(1) : '—' }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-4">
          <div class="card h-100">
            <div class="card-header"><strong>⚖️ Top Judges</strong></div>
            <div class="list-group list-group-flush">
              <div v-for="(entry, idx) in leaderboard.judges || []" :key="'j-'+idx"
                class="list-group-item d-flex justify-content-between">
                <span>
                  <strong class="mr-2">#{{ idx + 1 }}</strong>
                  <a :href="'/passport/profile/' + entry.user_id + '/'" class="text-dark">
                    {{ entry.display_name }}
                  </a>
                </span>
                <span class="text-muted">{{ entry.judge_rounds || 0 }} rounds</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PassportDirectory',
  data () {
    return {
      config: window.passportDirectoryConfig || {},
      passports: [],
      leaderboard: {},
      loading: true,
      searchQuery: '',
      searchTimeout: null,
      activeTab: 'directory',
      filters: {
        format: '',
        level: '',
      },
    }
  },
  watch: {
    activeTab (val) {
      if (val === 'leaderboard' && !this.leaderboard.speakers) {
        this.fetchLeaderboard()
      }
    },
  },
  mounted () {
    this.fetchPassports()
  },
  methods: {
    async fetchPassports () {
      this.loading = true
      try {
        const params = new URLSearchParams()
        if (this.searchQuery) params.set('search', this.searchQuery)
        if (this.filters.format) params.set('primary_format', this.filters.format)
        if (this.filters.level) params.set('experience_level', this.filters.level)

        const url = `${this.config.apiBase || '/passport/api/passports/'}?${params}`
        const res = await fetch(url)
        const data = await res.json()
        this.passports = data.results || data
      } catch (e) {
        console.error('Failed to fetch passports:', e)
      }
      this.loading = false
    },
    async fetchLeaderboard () {
      try {
        const res = await fetch(this.config.leaderboardUrl || '/passport/api/leaderboard/')
        if (res.ok) this.leaderboard = await res.json()
      } catch (e) { console.error(e) }
    },
    debounceSearch () {
      clearTimeout(this.searchTimeout)
      this.searchTimeout = setTimeout(() => this.fetchPassports(), 300)
    },
  },
}
</script>
