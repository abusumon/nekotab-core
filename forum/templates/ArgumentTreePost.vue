<template>
  <div class="argument-tree">
    <!-- Soft-deleted placeholder -->
    <div v-if="post.is_deleted" class="card mb-2 bg-light"
      :style="{'margin-left': indentPx + 'px'}">
      <div class="card-body py-2 px-3 text-muted" style="font-style: italic; font-size: 13px;">
        [deleted]
      </div>
      <!-- Still render children of deleted posts -->
      <argument-tree-post v-for="child in visibleChildren" :key="child.id"
        :post="child" :depth="depth + 1" :max-depth="maxDepth"
        :thread-locked="threadLocked" :is-authenticated="isAuthenticated"
        :is-staff="isStaff" :post-types="postTypes"
        @vote="$emit('vote', $event)"
        @reply="$emit('reply', $event)"
        @report="$emit('report', $event)"
        @delete-post="$emit('delete-post', $event)" />
    </div>

    <!-- Normal post -->
    <div v-else>
      <div class="card mb-2" :class="postTypeClass" :style="{'margin-left': indentPx + 'px'}">
        <div class="card-body py-2 px-3">
          <!-- Post type badge + meta -->
          <div class="d-flex align-items-center mb-2">
            <span v-if="post.post_type !== 'opening'" class="badge mr-2"
              :style="{backgroundColor: postTypeColor, color: '#fff'}">
              {{ postTypeIcon }} {{ post.post_type_display }}
            </span>
            <span class="text-muted small">
              <strong>{{ post.author_name }}</strong>
              <span v-for="badge in post.author_badges" :key="badge.id"
                class="badge badge-sm badge-success ml-1" :title="badge.badge_type_display">
                ✓
              </span>
              · {{ formatDate(post.created_at) }}
              <span v-if="post.is_edited" class="text-muted">(edited)</span>
            </span>
          </div>

          <!-- Content -->
          <div class="post-content mb-2" v-html="post.content"></div>

          <!-- Actions bar -->
          <div class="d-flex align-items-center flex-wrap" style="gap: 8px;">
            <!-- Vote buttons -->
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-secondary"
                :class="{'active': post.user_vote === 'up'}"
                @click="vote('up')" :title="isAuthenticated ? 'Upvote' : 'Login to vote'">
                ▲
              </button>
              <span class="btn btn-outline-secondary disabled">{{ post.vote_score }}</span>
              <button class="btn btn-outline-secondary"
                :class="{'active': post.user_vote === 'down'}"
                @click="vote('down')" :title="isAuthenticated ? 'Downvote' : 'Login to vote'">
                ▼
              </button>
            </div>

            <!-- Reply buttons (argument tree types) -->
            <div v-if="!threadLocked && isAuthenticated && depth < maxDepth"
              class="btn-group btn-group-sm">
              <button v-for="pt in replyTypes" :key="pt.value"
                class="btn btn-outline-secondary"
                :title="pt.label"
                @click="startReply(pt.value)">
                {{ pt.icon }}
              </button>
            </div>

            <!-- Generic reply for max-depth -->
            <button v-if="!threadLocked && isAuthenticated && depth >= maxDepth"
              class="btn btn-outline-secondary btn-sm" disabled title="Max nesting depth reached">
              ↩ Max depth
            </button>

            <!-- Report -->
            <button v-if="isAuthenticated" class="btn btn-outline-secondary btn-sm"
              @click="$emit('report', post.id)" title="Report">
              🚩
            </button>

            <!-- Delete (author or staff) -->
            <button v-if="isStaff" class="btn btn-outline-danger btn-sm"
              @click="$emit('delete-post', post.id)" title="Delete post">
              🗑️
            </button>
          </div>

          <!-- Inline reply form -->
          <div v-if="replyType" class="mt-3">
            <div class="form-group">
              <label class="small text-muted">
                Replying as: <strong>{{ replyLabel }}</strong>
              </label>
              <textarea v-model="replyContent" class="form-control" rows="3"
                placeholder="Write your response..."></textarea>
            </div>
            <div class="d-flex" style="gap: 8px;">
              <button class="btn btn-primary btn-sm" @click="submitReply" :disabled="!replyContent.trim()">
                Post Reply
              </button>
              <button class="btn btn-outline-secondary btn-sm" @click="cancelReply">Cancel</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Children (recursive) — only render if under max depth -->
      <argument-tree-post v-for="child in visibleChildren" :key="child.id"
        :post="child" :depth="depth + 1" :max-depth="maxDepth"
        :thread-locked="threadLocked" :is-authenticated="isAuthenticated"
        :is-staff="isStaff" :post-types="postTypes"
        @vote="$emit('vote', $event)"
        @reply="$emit('reply', $event)"
        @report="$emit('report', $event)"
        @delete-post="$emit('delete-post', $event)" />

      <!-- "Continue thread" link for collapsed children -->
      <div v-if="collapsedCount > 0" :style="{'margin-left': ((depth + 1) * 24) + 'px'}">
        <button class="btn btn-link btn-sm text-muted" @click="showAll = true">
          ↳ {{ collapsedCount }} more {{ collapsedCount === 1 ? 'reply' : 'replies' }} (continue thread)
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ArgumentTreePost',
  props: {
    post: { type: Object, required: true },
    depth: { type: Number, default: 0 },
    maxDepth: { type: Number, default: 6 },
    threadLocked: { type: Boolean, default: false },
    isAuthenticated: { type: Boolean, default: false },
    isStaff: { type: Boolean, default: false },
    postTypes: { type: Array, default: () => [] },
  },
  data () {
    return {
      replyType: null,
      replyContent: '',
      showAll: false,
    }
  },
  computed: {
    indentPx () {
      return Math.min(this.depth, 8) * 24
    },
    replyTypes () {
      return this.postTypes.filter(pt => pt.value !== 'opening')
    },
    allChildren () {
      return (this.post.children || []).filter(c => true)
    },
    visibleChildren () {
      if (this.showAll || this.depth < this.maxDepth) return this.allChildren
      return []
    },
    collapsedCount () {
      if (this.showAll || this.depth < this.maxDepth) return 0
      return this.allChildren.length
    },
    postTypeColor () {
      const pt = this.postTypes.find(p => p.value === this.post.post_type)
      return pt ? pt.color : '#6c757d'
    },
    postTypeIcon () {
      const pt = this.postTypes.find(p => p.value === this.post.post_type)
      return pt ? pt.icon : ''
    },
    postTypeClass () {
      const t = this.post.post_type
      if (t === 'counter' || t === 'rebuttal') return 'border-left-danger'
      if (t === 'support') return 'border-left-success'
      if (t === 'framework') return 'border-left-info'
      return ''
    },
    replyLabel () {
      const pt = this.postTypes.find(p => p.value === this.replyType)
      return pt ? `${pt.icon} ${pt.label}` : ''
    },
  },
  methods: {
    startReply (type) {
      this.replyType = type
      this.replyContent = ''
    },
    cancelReply () {
      this.replyType = null
      this.replyContent = ''
    },
    submitReply () {
      this.$emit('reply', {
        thread: this.post.thread,
        parent: this.post.id,
        post_type: this.replyType,
        content: this.replyContent,
      })
      this.cancelReply()
    },
    vote (type) {
      this.$emit('vote', { post_id: this.post.id, vote_type: type })
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
