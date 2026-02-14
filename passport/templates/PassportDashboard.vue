<template>
  <div class="passport-dashboard">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
    </div>

    <div v-else-if="passport">
      <h2 class="mb-4">📊 My Debate Analytics</h2>

      <!-- Summary Cards -->
      <div class="row mb-4">
        <div class="col-6 col-md-2 mb-3" v-for="stat in summaryCards" :key="stat.label">
          <div class="card text-center h-100">
            <div class="card-body py-3">
              <h4 class="mb-0">{{ stat.value }}</h4>
              <small class="text-muted">{{ stat.label }}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- Skill Radar -->
      <div v-if="stats.skill_radar" class="card mb-4">
        <div class="card-header"><strong>🎯 Skill Radar</strong></div>
        <div class="card-body">
          <div class="row">
            <div v-for="(value, skill) in stats.skill_radar" :key="skill" class="col-6 col-md-4 col-lg-3 mb-3">
              <div class="d-flex justify-content-between mb-1">
                <span class="text-capitalize font-weight-bold">{{ skill }}</span>
                <span :class="skillTextClass(value)">{{ value }}/100</span>
              </div>
              <div class="progress" style="height: 12px;">
                <div class="progress-bar" :class="skillBarClass(value)"
                  :style="{ width: value + '%' }" role="progressbar"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Win Rate Breakdown -->
      <div class="row mb-4">
        <div class="col-md-6">
          <div class="card h-100">
            <div class="card-header"><strong>Win Rates</strong></div>
            <div class="card-body">
              <div v-for="item in winRateItems" :key="item.label" class="mb-3">
                <div class="d-flex justify-content-between mb-1">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.pct }}</strong>
                </div>
                <div class="progress" style="height: 8px;">
                  <div class="progress-bar" :class="item.color"
                    :style="{ width: item.pct }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card h-100">
            <div class="card-header"><strong>Format Distribution</strong></div>
            <div class="card-body">
              <div v-if="stats.format_distribution">
                <div v-for="(count, fmt) in stats.format_distribution" :key="fmt" class="mb-2">
                  <div class="d-flex justify-content-between">
                    <span>{{ fmt }}</span>
                    <span class="badge badge-primary">{{ count }}</span>
                  </div>
                </div>
              </div>
              <p v-else class="text-muted">No format data yet.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Performance Trend -->
      <div v-if="stats.performance_trend && stats.performance_trend.length" class="card mb-4">
        <div class="card-header"><strong>📈 Performance Over Time</strong></div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Tournaments</th>
                  <th>Avg Score</th>
                  <th>Win Rate</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in stats.performance_trend" :key="t.year">
                  <td>{{ t.year }}</td>
                  <td>{{ t.tournaments }}</td>
                  <td>{{ t.avg_score ? t.avg_score.toFixed(1) : '—' }}</td>
                  <td>{{ t.win_rate ? t.win_rate.toFixed(0) + '%' : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Judge Analytics -->
      <div v-if="stats.judge_total_rounds > 0" class="card mb-4">
        <div class="card-header"><strong>⚖️ Judging Analytics</strong></div>
        <div class="card-body">
          <div class="row">
            <div class="col-6 col-md-3 text-center">
              <h4>{{ stats.judge_total_rounds }}</h4>
              <small class="text-muted">Rounds Judged</small>
            </div>
            <div class="col-6 col-md-3 text-center">
              <h4>{{ stats.judge_chair_rate ? stats.judge_chair_rate.toFixed(0) + '%' : '—' }}</h4>
              <small class="text-muted">Chair Rate</small>
            </div>
            <div class="col-6 col-md-3 text-center">
              <h4>{{ stats.judge_avg_score_given ? stats.judge_avg_score_given.toFixed(1) : '—' }}</h4>
              <small class="text-muted">Avg Score Given</small>
            </div>
            <div class="col-6 col-md-3 text-center">
              <h4>{{ stats.judge_majority_agreement ? stats.judge_majority_agreement.toFixed(0) + '%' : '—' }}</h4>
              <small class="text-muted">Majority Agreement</small>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="mt-3">
        <button class="btn btn-primary" @click="recomputeStats" :disabled="recomputing">
          {{ recomputing ? 'Recomputing...' : '🔄 Recompute Stats' }}
        </button>
        <a href="/passport/edit/" class="btn btn-outline-secondary ml-2">✏️ Edit Profile</a>
      </div>
    </div>

    <div v-else class="alert alert-info">
      <p>You haven't created a Debate Passport yet.</p>
      <a href="/passport/edit/" class="btn btn-primary">Create Passport</a>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PassportDashboard',
  data () {
    return {
      passport: null,
      stats: {},
      loading: true,
      recomputing: false,
    }
  },
  computed: {
    summaryCards () {
      const s = this.stats
      return [
        { label: 'Tournaments', value: s.total_tournaments || 0 },
        { label: 'Rounds', value: s.total_rounds || 0 },
        { label: 'Win Rate', value: s.overall_win_rate ? s.overall_win_rate.toFixed(0) + '%' : '—' },
        { label: 'Avg Score', value: s.average_speaker_score ? s.average_speaker_score.toFixed(1) : '—' },
        { label: 'Break Rate', value: s.break_rate ? s.break_rate.toFixed(0) + '%' : '—' },
        { label: 'Best Score', value: s.highest_speaker_score || '—' },
      ]
    },
    winRateItems () {
      const s = this.stats
      return [
        { label: 'Overall', pct: this.pct(s.overall_win_rate), color: 'bg-primary' },
        { label: 'Gov / Prop', pct: this.pct(s.gov_win_rate), color: 'bg-success' },
        { label: 'Opp', pct: this.pct(s.opp_win_rate), color: 'bg-danger' },
      ]
    },
  },
  mounted () {
    this.fetchDashboard()
  },
  methods: {
    async fetchDashboard () {
      const config = window.passportDashboardConfig || {}
      try {
        const res = await fetch(config.meUrl || '/passport/api/passports/me/')
        if (!res.ok) { this.loading = false; return }
        this.passport = await res.json()
        this.stats = this.passport.stats || {}
      } catch (e) { console.error(e) }
      this.loading = false
    },
    async recomputeStats () {
      this.recomputing = true
      const csrfToken = this.getCsrf()
      const config = window.passportDashboardConfig || {}
      try {
        await fetch(config.recomputeUrl || '/passport/api/recompute/', {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken },
        })
        await this.fetchDashboard()
      } catch (e) { console.error(e) }
      this.recomputing = false
    },
    pct (rate) {
      if (rate === null || rate === undefined) return '0%'
      return rate.toFixed(0) + '%'
    },
    skillBarClass (v) {
      if (v >= 80) return 'bg-success'
      if (v >= 50) return 'bg-primary'
      if (v >= 30) return 'bg-warning'
      return 'bg-danger'
    },
    skillTextClass (v) {
      if (v >= 80) return 'text-success'
      if (v >= 50) return 'text-primary'
      if (v >= 30) return 'text-warning'
      return 'text-danger'
    },
    getCsrf () {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || ''
    },
  },
}
</script>
