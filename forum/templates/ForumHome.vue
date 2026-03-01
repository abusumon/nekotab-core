<template>
  <div class="forum-home">
    <!-- Sort Tabs -->
    <div class="d-flex align-items-center mb-3" style="gap: 6px;">
      <button class="btn btn-sm" :class="activeSort === 'hot' ? 'btn-primary' : 'btn-outline-secondary'"
        @click="setSort('hot')">🔥 Hot</button>
      <button class="btn btn-sm" :class="activeSort === 'new' ? 'btn-primary' : 'btn-outline-secondary'"
        @click="setSort('new')">🕐 New</button>
      <button class="btn btn-sm" :class="activeSort === 'top' ? 'btn-primary' : 'btn-outline-secondary'"
        @click="setSort('top')">🔝 Top</button>
      <div class="ml-auto">
        <a v-if="config.isAuthenticated" :href="config.createUrl" class="btn btn-primary btn-sm">
          ✏️ New Discussion
        </a>
        <a v-else href="/accounts/login/" class="btn btn-outline-primary btn-sm">Login to Post</a>
      </div>
    </div>

    <!-- Search & Filter Bar -->
    <div class="card mb-3">
      <div class="card-body py-2 px-3">
        <div class="row">
          <div class="col-md-4 mb-2">
            <input v-model="searchQuery" type="text" class="form-control form-control-sm"
              placeholder="Search discussions..." @input="debounceSearch" />
          </div>
          <div class="col-md-3 mb-2">
            <select v-model="filters.format" class="form-control form-control-sm" @change="fetchThreads">
              <option value="">All Formats</option>
              <option v-for="f in config.formats" :key="f.value" :value="f.value">{{ f.label }}</option>
            </select>
          </div>
          <div class="col-md-3 mb-2">
            <select v-model="filters.category" class="form-control form-control-sm" @change="fetchThreads">
              <option value="">All Categories</option>
              <option v-for="c in config.categories" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <select v-model="filters.skill" class="form-control form-control-sm" @change="fetchThreads">
              <option value="">All Levels</option>
              <option v-for="s in config.skillLevels" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="alert alert-danger alert-dismissible fade show" role="alert">
      {{ error }}
      <button type="button" class="close" @click="error = null"><span>&times;</span></button>
    </div>

    <!-- Thread List -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="sr-only">Loading...</span>
      </div>
    </div>

    <div v-else>
      <div v-for="thread in threads" :key="thread.id" class="card mb-2 forum-thread-card"
           :class="{'border-primary': thread.is_pinned}">
        <div class="card-body py-3 px-3">
          <div class="d-flex justify-content-between align-items-start">
            <!-- Vote column -->
            <div class="text-center mr-3" style="min-width: 40px;">
              <div class="text-muted" style="font-size: 18px; font-weight: 700; line-height: 1;">
                {{ thread.score || 0 }}
              </div>
              <div class="text-muted small">score</div>
            </div>

            <div class="flex-grow-1">
              <div class="d-flex align-items-center mb-1">
                <span v-if="thread.is_pinned" class="badge badge-warning mr-2">📌</span>
                <span v-if="thread.is_locked" class="badge badge-dark mr-1">🔒</span>
                <a :href="'/forum/thread/' + thread.slug + '/'" class="h6 mb-0 text-dark text-decoration-none">
                  {{ thread.title }}
                </a>
              </div>
              <div class="d-flex flex-wrap align-items-center text-muted small" style="gap: 6px;">
                <span class="badge badge-outline-primary">{{ thread.format_display }}</span>
                <span class="badge badge-outline-secondary">{{ thread.category_display }}</span>
                <span class="badge badge-outline-info">{{ thread.skill_display }}</span>
                <span v-for="tag in thread.tags" :key="tag.id"
                  class="badge" :style="{backgroundColor: tag.color, color: '#fff'}">
                  {{ tag.name }}
                </span>
                <span class="ml-2">by <strong>{{ thread.author_name }}</strong></span>
                <span v-for="badge in thread.author_badges" :key="badge.id"
                  class="badge badge-sm badge-success" :title="badge.badge_type_display">
                  ✓ {{ badge.badge_type_display }}
                </span>
              </div>
            </div>
            <div class="text-right text-muted small" style="min-width: 80px;">
              <div>💬 {{ thread.comment_count || thread.reply_count || 0 }}</div>
              <div>👁 {{ thread.view_count }}</div>
              <div>{{ formatDate(thread.last_activity || thread.updated_at) }}</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="threads.length === 0" class="card">
        <div class="card-body text-center py-5">
          <h5 class="text-muted">No discussions found</h5>
          <p class="text-muted">Try adjusting your filters or start a new discussion.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ForumHome',
  data () {
    return {
      config: window.forumConfig || {},
      threads: [],
      loading: true,
      error: null,
      searchQuery: '',
      searchTimeout: null,
      activeSort: 'hot',
      filters: {
        format: '',
        category: '',
        skill: '',
      },
    }
  },
  mounted () {
    this.fetchThreads()
  },
  methods: {
    setSort (sort) {
      this.activeSort = sort
      this.fetchThreads()
    },
    async fetchThreads () {
      this.loading = true
      this.error = null
      try {
        const params = new URLSearchParams()
        params.set('sort', this.activeSort)
        if (this.searchQuery) params.set('search', this.searchQuery)
        if (this.filters.format) params.set('format', this.filters.format)
        if (this.filters.category) params.set('category', this.filters.category)
        if (this.filters.skill) params.set('skill', this.filters.skill)

        const url = `${this.config.apiBase}?${params.toString()}`
        const response = await fetch(url)
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const data = await response.json()
        this.threads = data.results || data
      } catch (e) {
        this.error = `Failed to load discussions: ${e.message}`
        console.error('Failed to fetch threads:', e)
      }
      this.loading = false
    },
    debounceSearch () {
      clearTimeout(this.searchTimeout)
      this.searchTimeout = setTimeout(() => this.fetchThreads(), 300)
    },
    formatDate (dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      const now = new Date()
      const diff = now - date
      const minutes = Math.floor(diff / 60000)
      if (minutes < 60) return `${minutes}m ago`
      const hours = Math.floor(minutes / 60)
      if (hours < 24) return `${hours}h ago`
      const days = Math.floor(hours / 24)
      if (days < 30) return `${days}d ago`
      return date.toLocaleDateString()
    },
  },
}
</script>
