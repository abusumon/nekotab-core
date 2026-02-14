<template>
  <div class="passport-profile">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
    </div>

    <div v-else-if="passport">
      <!-- Profile Header -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="d-flex align-items-start">
            <div class="mr-4">
              <div class="avatar-lg rounded-circle bg-primary text-white d-flex align-items-center justify-content-center"
                style="width:80px; height:80px; font-size:2rem;">
                {{ passport.display_name ? passport.display_name[0].toUpperCase() : '?' }}
              </div>
            </div>
            <div class="flex-grow-1">
              <h2 class="mb-1">{{ passport.display_name }}</h2>
              <div class="mb-2">
                <span v-if="passport.country" class="mr-2">
                  {{ passport.country_code ? flagEmoji(passport.country_code) : '🌍' }} {{ passport.country }}
                </span>
                <span v-if="passport.institution" class="text-muted">· 🏫 {{ passport.institution }}</span>
              </div>
              <div class="mb-2">
                <span v-if="passport.is_speaker" class="badge badge-primary mr-1">🎤 Speaker</span>
                <span v-if="passport.is_judge" class="badge badge-info mr-1">⚖️ Judge</span>
                <span v-if="passport.is_ca" class="badge badge-warning mr-1">👑 CA</span>
                <span v-if="passport.is_coach" class="badge badge-success mr-1">📋 Coach</span>
              </div>
              <div v-if="passport.badges && passport.badges.length" class="mb-2">
                <span v-for="badge in passport.badges" :key="badge.id"
                  class="badge badge-pill badge-success mr-1">
                  ✓ {{ badge.badge_type_display }}
                </span>
              </div>
              <p v-if="passport.bio" class="text-muted mt-2">{{ passport.bio }}</p>
              <div v-if="isOwn" class="mt-2">
                <a :href="editUrl" class="btn btn-sm btn-outline-primary">✏️ Edit Profile</a>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Stats Overview -->
      <div v-if="passport.stats" class="row mb-4">
        <div class="col-6 col-md-3 mb-3">
          <div class="card text-center h-100">
            <div class="card-body py-3">
              <h3 class="mb-0">{{ passport.stats.total_tournaments }}</h3>
              <small class="text-muted">Tournaments</small>
            </div>
          </div>
        </div>
        <div class="col-6 col-md-3 mb-3">
          <div class="card text-center h-100">
            <div class="card-body py-3">
              <h3 class="mb-0">{{ passport.stats.total_rounds }}</h3>
              <small class="text-muted">Rounds</small>
            </div>
          </div>
        </div>
        <div class="col-6 col-md-3 mb-3">
          <div class="card text-center h-100">
            <div class="card-body py-3">
              <h3 class="mb-0">{{ passport.stats.average_speaker_score ? passport.stats.average_speaker_score.toFixed(1) : '—' }}</h3>
              <small class="text-muted">Avg Speaker Score</small>
            </div>
          </div>
        </div>
        <div class="col-6 col-md-3 mb-3">
          <div class="card text-center h-100">
            <div class="card-body py-3">
              <h3 class="mb-0">{{ passport.stats.break_rate ? passport.stats.break_rate.toFixed(0) + '%' : '—' }}</h3>
              <small class="text-muted">Break Rate</small>
            </div>
          </div>
        </div>
      </div>

      <!-- Skill Radar -->
      <div v-if="passport.stats && passport.stats.skill_radar" class="card mb-4">
        <div class="card-header"><strong>📊 Skill Radar</strong></div>
        <div class="card-body">
          <div class="row">
            <div v-for="(value, skill) in passport.stats.skill_radar" :key="skill" class="col-6 col-md-4 mb-3">
              <div class="d-flex justify-content-between mb-1">
                <small class="text-capitalize">{{ skill }}</small>
                <small>{{ value }}/100</small>
              </div>
              <div class="progress" style="height: 8px;">
                <div class="progress-bar" :class="skillBarClass(value)"
                  :style="{ width: value + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Win Rates -->
      <div v-if="passport.stats" class="card mb-4">
        <div class="card-header"><strong>📈 Win Rates</strong></div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-4">
              <h5>Overall: {{ winPct(passport.stats.overall_win_rate) }}</h5>
            </div>
            <div class="col-md-4">
              <small class="text-muted">Gov/Prop:</small> {{ winPct(passport.stats.gov_win_rate) }}
            </div>
            <div class="col-md-4">
              <small class="text-muted">Opp:</small> {{ winPct(passport.stats.opp_win_rate) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Tournament History -->
      <div v-if="participations.length" class="card mb-4">
        <div class="card-header"><strong>🏆 Tournament History</strong></div>
        <div class="table-responsive">
          <table class="table table-sm mb-0">
            <thead>
              <tr>
                <th>Tournament</th>
                <th>Year</th>
                <th>Format</th>
                <th>Role</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in participations" :key="p.id">
                <td>{{ p.tournament_name }}</td>
                <td>{{ p.year }}</td>
                <td>{{ p.tournament_format }}</td>
                <td>{{ p.role }}</td>
                <td>
                  <span v-if="p.broke" class="badge badge-success">Broke</span>
                  <span v-if="p.break_category" class="text-muted ml-1">{{ p.break_category }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Partnerships -->
      <div v-if="passport.partnerships && passport.partnerships.length" class="card mb-4">
        <div class="card-header"><strong>🤝 Partnerships</strong></div>
        <div class="list-group list-group-flush">
          <div v-for="p in passport.partnerships" :key="p.id" class="list-group-item">
            <div class="d-flex justify-content-between">
              <strong>{{ p.partner_name }}</strong>
              <span class="text-muted">{{ p.tournaments_together }} tournaments · {{ p.rounds_together }} rounds</span>
            </div>
            <small>Win rate: {{ winPct(p.win_rate) }} · Avg score: {{ p.avg_speaker_score ? p.avg_speaker_score.toFixed(1) : '—' }}</small>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="alert alert-warning">Passport not found or is private.</div>
  </div>
</template>

<script>
export default {
  name: 'PassportProfile',
  data () {
    return {
      passport: null,
      participations: [],
      loading: true,
      isOwn: false,
      editUrl: '/passport/edit/',
    }
  },
  mounted () {
    this.fetchProfile()
  },
  methods: {
    async fetchProfile () {
      const config = window.passportProfileConfig || {}
      const userId = config.userId
      const isOwn = config.isOwn || false
      this.isOwn = isOwn

      const url = config.apiUrl || (isOwn ? '/passport/api/passports/me/' : `/passport/api/passports/${userId}/`)
      try {
        const res = await fetch(url)
        if (!res.ok) throw new Error('Not found')
        this.passport = await res.json()

        // Fetch participations
        if (this.passport && this.passport.id) {
          const tournamentsUrl = config.tournamentsUrl || '/passport/api/tournaments/'
          const pRes = await fetch(`${tournamentsUrl}?passport=${this.passport.id}`)
          if (pRes.ok) this.participations = await pRes.json()
        }
      } catch (e) { console.error(e) }
      this.loading = false
    },
    flagEmoji (code) {
      if (!code || code.length !== 2) return '🌍'
      return String.fromCodePoint(
        ...[...code.toUpperCase()].map(c => 0x1F1E6 + c.charCodeAt(0) - 65),
      )
    },
    winPct (rate) {
      if (rate === null || rate === undefined) return '—'
      return rate.toFixed(0) + '%'
    },
    skillBarClass (value) {
      if (value >= 80) return 'bg-success'
      if (value >= 50) return 'bg-primary'
      if (value >= 30) return 'bg-warning'
      return 'bg-danger'
    },
  },
}
</script>
