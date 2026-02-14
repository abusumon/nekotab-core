<template>
  <div class="forum-create">
    <div class="card">
      <div class="card-header"><strong>✏️ Start a New Discussion</strong></div>
      <div class="card-body">
        <div class="form-group">
          <label>Title</label>
          <input v-model="form.title" class="form-control" placeholder="What do you want to discuss?" maxlength="300" />
        </div>

        <div class="row">
          <div class="col-md-4 form-group">
            <label>Debate Format</label>
            <select v-model="form.debate_format" class="form-control">
              <option value="bp">British Parliamentary</option>
              <option value="wsdc">World Schools</option>
              <option value="ap">Australs / Asian Parliamentary</option>
              <option value="pf">Public Forum</option>
              <option value="ld">Lincoln-Douglas</option>
              <option value="policy">Policy</option>
              <option value="cp">Canadian Parliamentary</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div class="col-md-4 form-group">
            <label>Topic Category</label>
            <select v-model="form.topic_category" class="form-control">
              <option value="theory">Theory & Principles</option>
              <option value="strategy">Strategy & Technique</option>
              <option value="motions">Motion Analysis</option>
              <option value="judge_issues">Judging Issues</option>
              <option value="meta">Meta</option>
              <option value="case_study">Case Study</option>
              <option value="training">Training & Coaching</option>
            </select>
          </div>
          <div class="col-md-4 form-group">
            <label>Skill Level</label>
            <select v-model="form.skill_level" class="form-control">
              <option value="all">All Levels</option>
              <option value="novice">Novice</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>Region (optional)</label>
          <input v-model="form.region" class="form-control" placeholder="e.g., Asia, Europe, North America" />
        </div>

        <div class="form-group">
          <label>Tags</label>
          <div>
            <span v-for="tag in availableTags" :key="tag.id"
              class="badge mr-1 mb-1" style="cursor:pointer"
              :class="selectedTags.includes(tag.id) ? 'badge-primary' : 'badge-light'"
              @click="toggleTag(tag.id)">
              {{ tag.name }}
            </span>
          </div>
        </div>

        <div class="form-group">
          <label>Your Opening Post</label>
          <textarea v-model="form.initial_post" class="form-control" rows="8"
            placeholder="Share your thoughts, analysis, or question..."></textarea>
        </div>

        <div class="d-flex justify-content-between">
          <a href="/forum/" class="btn btn-outline-secondary">Cancel</a>
          <button class="btn btn-primary" @click="submit"
            :disabled="!canSubmit || submitting">
            {{ submitting ? 'Creating...' : '🚀 Create Discussion' }}
          </button>
        </div>

        <div v-if="error" class="alert alert-danger mt-3">{{ error }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ForumCreate',
  data () {
    return {
      form: {
        title: '',
        debate_format: 'bp',
        topic_category: 'theory',
        skill_level: 'all',
        region: '',
        initial_post: '',
      },
      selectedTags: [],
      availableTags: [],
      submitting: false,
      error: null,
    }
  },
  computed: {
    canSubmit () {
      return this.form.title.trim() && this.form.initial_post.trim()
    },
  },
  mounted () {
    this.fetchTags()
  },
  methods: {
    async fetchTags () {
      const config = window.forumCreateConfig || {}
      try {
        const res = await fetch(config.tagsUrl || '/forum/api/tags/')
        if (res.ok) this.availableTags = await res.json()
      } catch (e) { console.error(e) }
    },
    toggleTag (id) {
      const idx = this.selectedTags.indexOf(id)
      if (idx >= 0) this.selectedTags.splice(idx, 1)
      else this.selectedTags.push(id)
    },
    async submit () {
      this.submitting = true
      this.error = null
      const csrfToken = this.getCsrf()
      const config = window.forumCreateConfig || {}

      try {
        const res = await fetch(config.apiUrl || '/forum/api/threads/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({
            ...this.form,
            tag_ids: this.selectedTags,
          }),
        })
        if (res.ok) {
          const data = await res.json()
          window.location.href = `/forum/thread/${data.slug}/`
        } else {
          const err = await res.json()
          this.error = Object.values(err).flat().join(', ') || 'Failed to create thread.'
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
