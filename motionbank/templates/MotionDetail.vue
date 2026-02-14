<template>
  <div class="motion-detail">
    <!-- Loading -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
    </div>

    <div v-else-if="motion">
      <!-- Header -->
      <div class="card mb-4">
        <div class="card-body">
          <h2 class="mb-3">{{ motion.text }}</h2>
          <div class="d-flex flex-wrap mb-2">
            <span class="badge badge-primary mr-2">{{ motion.format_display }}</span>
            <span class="badge mr-2" :class="difficultyClass">{{ motion.difficulty_display }}</span>
            <span class="badge badge-secondary mr-2">{{ motion.type_display }}</span>
            <span class="badge badge-outline-info mr-2" v-if="motion.prep_display">{{ motion.prep_display }}</span>
          </div>
          <p v-if="motion.tournament_name" class="text-muted mb-1">
            🏆 {{ motion.tournament_name }} <span v-if="motion.year">({{ motion.year }})</span>
            <span v-if="motion.round_info"> — {{ motion.round_info }}</span>
          </p>
          <p v-if="motion.region" class="text-muted mb-1">📍 {{ motion.region }}</p>
          <div v-if="motion.info_slide" class="alert alert-info mt-3">
            <strong>Info Slide:</strong> {{ motion.info_slide }}
          </div>
          <div v-if="motion.theme_tags && motion.theme_tags.length" class="mt-2">
            <span v-for="tag in motion.theme_tags" :key="tag"
              class="badge badge-light mr-1">#{{ tag }}</span>
          </div>
        </div>
      </div>

      <!-- Rating -->
      <div class="card mb-4">
        <div class="card-body d-flex align-items-center">
          <strong class="mr-3">Rate this motion:</strong>
          <span v-for="star in 5" :key="star"
            class="star-btn" :class="{ active: star <= (userRating || 0) }"
            @click="rateMotion(star)" style="cursor:pointer; font-size:1.5rem; margin-right:4px;">
            {{ star <= (userRating || 0) ? '★' : '☆' }}
          </span>
          <span v-if="motion.stats" class="ml-3 text-muted">
            {{ motion.stats.average_rating.toFixed(1) }}/5 ({{ motion.stats.total_ratings }} ratings)
          </span>
        </div>
      </div>

      <!-- AI Analysis -->
      <div v-if="motion.analysis && motion.analysis.ai_analysis" class="card mb-4">
        <div class="card-header bg-primary text-white">
          <strong>🩺 Motion Doctor Analysis</strong>
          <small class="float-right" v-if="motion.analysis.model_used">
            Model: {{ motion.analysis.model_used }}
          </small>
        </div>
        <div class="card-body">
          <div v-if="motion.analysis.ai_analysis.clash_areas" class="mb-3">
            <h6>⚔️ Clash Areas</h6>
            <ul><li v-for="(c, i) in motion.analysis.ai_analysis.clash_areas" :key="'c'+i">{{ c }}</li></ul>
          </div>
          <div class="row">
            <div class="col-md-6" v-if="motion.analysis.ai_analysis.gov_approach">
              <h6>🟢 Gov Approach</h6>
              <p><strong>Structure:</strong> {{ motion.analysis.ai_analysis.gov_approach.structure }}</p>
              <ul><li v-for="(a, i) in motion.analysis.ai_analysis.gov_approach.key_args" :key="'ga'+i">{{ a }}</li></ul>
            </div>
            <div class="col-md-6" v-if="motion.analysis.ai_analysis.opp_approach">
              <h6>🔴 Opp Approach</h6>
              <p><strong>Structure:</strong> {{ motion.analysis.ai_analysis.opp_approach.structure }}</p>
              <ul><li v-for="(a, i) in motion.analysis.ai_analysis.opp_approach.key_args" :key="'oa'+i">{{ a }}</li></ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Case Outlines -->
      <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <strong>📝 Community Case Outlines</strong>
          <button class="btn btn-sm btn-outline-primary" @click="showOutlineForm = !showOutlineForm">
            {{ showOutlineForm ? 'Cancel' : '+ Add Outline' }}
          </button>
        </div>
        <div class="card-body">
          <!-- Submit form -->
          <div v-if="showOutlineForm" class="mb-4 p-3 bg-light rounded">
            <div class="form-group">
              <label>Side</label>
              <select v-model="newOutline.side" class="form-control form-control-sm">
                <option value="gov">Government / Proposition</option>
                <option value="opp">Opposition</option>
                <option value="og">Opening Government</option>
                <option value="oo">Opening Opposition</option>
                <option value="cg">Closing Government</option>
                <option value="co">Closing Opposition</option>
              </select>
            </div>
            <div class="form-group">
              <label>Title</label>
              <input v-model="newOutline.title" class="form-control form-control-sm"
                placeholder="e.g., Rights-based Gov case" />
            </div>
            <div class="form-group">
              <label>Content</label>
              <textarea v-model="newOutline.content" class="form-control form-control-sm"
                rows="6" placeholder="Your case outline..."></textarea>
            </div>
            <button class="btn btn-primary btn-sm" @click="submitOutline"
              :disabled="!newOutline.title || !newOutline.content">Submit</button>
          </div>

          <!-- Outlines list -->
          <div v-if="motion.case_outlines && motion.case_outlines.length">
            <div v-for="outline in motion.case_outlines" :key="outline.id" class="mb-3 p-3 border rounded">
              <div class="d-flex justify-content-between">
                <div>
                  <span class="badge badge-info mr-2">{{ outline.side_display }}</span>
                  <strong>{{ outline.title }}</strong>
                  <small class="text-muted ml-2">by {{ outline.author_name }}</small>
                </div>
                <button class="btn btn-sm" :class="outline.user_voted ? 'btn-success' : 'btn-outline-success'"
                  @click="voteOutline(outline)">
                  👍 {{ outline.upvotes }}
                </button>
              </div>
              <p class="mt-2 mb-0" style="white-space:pre-wrap;">{{ outline.content }}</p>
            </div>
          </div>
          <p v-else class="text-muted">No case outlines yet. Be the first to contribute!</p>
        </div>
      </div>

      <!-- Related Motions -->
      <div v-if="motion.related_motions && motion.related_motions.length" class="card mb-4">
        <div class="card-header"><strong>🔗 Related Motions</strong></div>
        <div class="list-group list-group-flush">
          <a v-for="rm in motion.related_motions" :key="rm.id"
            :href="'/motions-bank/motion/' + rm.slug + '/'"
            class="list-group-item list-group-item-action">
            {{ rm.text }}
            <span class="badge badge-light float-right">{{ rm.format_display }}</span>
          </a>
        </div>
      </div>

      <!-- Forum Threads -->
      <div v-if="motion.forum_threads && motion.forum_threads.length" class="card mb-4">
        <div class="card-header"><strong>💬 Forum Discussions</strong></div>
        <div class="list-group list-group-flush">
          <a v-for="thread in motion.forum_threads" :key="thread.id"
            :href="'/forum/thread/' + thread.slug + '/'"
            class="list-group-item list-group-item-action">
            {{ thread.title }}
          </a>
        </div>
      </div>
    </div>

    <div v-else class="alert alert-warning">Motion not found.</div>
  </div>
</template>

<script>
export default {
  name: 'MotionDetail',
  data () {
    return {
      motion: null,
      userRating: null,
      loading: true,
      showOutlineForm: false,
      newOutline: { side: 'gov', title: '', content: '' },
    }
  },
  computed: {
    difficultyClass () {
      if (!this.motion) return 'badge-secondary'
      const map = { 1: 'badge-success', 2: 'badge-info', 3: 'badge-warning', 4: 'badge-danger', 5: 'badge-dark' }
      return map[this.motion.difficulty] || 'badge-secondary'
    },
  },
  mounted () {
    this.fetchMotion()
  },
  methods: {
    async fetchMotion () {
      const config = window.motionDetailConfig || {}
      const url = config.apiUrl
      if (!url) { this.loading = false; return }

      try {
        const res = await fetch(url)
        if (!res.ok) throw new Error('Not found')
        this.motion = await res.json()
        this.userRating = this.motion.user_rating
      } catch (e) {
        console.error(e)
      }
      this.loading = false
    },
    async rateMotion (score) {
      const csrfToken = this.getCsrf()
      const config = window.motionDetailConfig || {}
      try {
        await fetch(config.rateUrl || '/motions-bank/api/rate/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({ motion: this.motion.id, score }),
        })
        this.userRating = score
        this.fetchMotion()
      } catch (e) { console.error(e) }
    },
    async submitOutline () {
      const csrfToken = this.getCsrf()
      const config = window.motionDetailConfig || {}
      try {
        const res = await fetch(config.outlinesUrl || `/motions-bank/api/outlines/${this.motion.id}/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(this.newOutline),
        })
        if (res.ok) {
          this.showOutlineForm = false
          this.newOutline = { side: 'gov', title: '', content: '' }
          this.fetchMotion()
        }
      } catch (e) { console.error(e) }
    },
    async voteOutline (outline) {
      const csrfToken = this.getCsrf()
      await fetch(`/motions-bank/api/outlines/${outline.id}/vote/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      })
      this.fetchMotion()
    },
    getCsrf () {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || ''
    },
  },
}
</script>
