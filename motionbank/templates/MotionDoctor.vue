<template>
  <div class="motion-doctor">
    <!-- ===== INPUT PANEL ===== -->
    <div class="card mb-4 shadow-sm border-0">
      <div class="card-body p-4">
        <div class="d-flex align-items-center mb-3">
          <span class="mr-2" style="font-size:1.75rem">🩺</span>
          <div>
            <h3 class="mb-0 font-weight-bold">Motion Doctor</h3>
            <p class="text-muted mb-0 small">AI-powered 4-stage analysis: Profiler → Planner → Generator → Validator</p>
          </div>
        </div>

        <div class="form-group mb-3">
          <label class="font-weight-bold small text-uppercase text-muted">Motion Text</label>
          <textarea v-model="motionText" class="form-control form-control-lg" rows="3"
            placeholder="e.g., This House Would ban all forms of genetic engineering on humans"
            :disabled="analyzing"
            style="font-size:1.05rem; border-radius:10px;"></textarea>
        </div>

        <div class="form-group mb-3">
          <label class="font-weight-bold small text-uppercase text-muted">Info Slide (optional)</label>
          <textarea v-model="infoSlide" class="form-control" rows="2"
            placeholder="Paste the infoslide here if the motion has one..."
            :disabled="analyzing"
            style="border-radius:10px;"></textarea>
        </div>

        <div class="row mb-3">
          <div class="col-md-4 mb-2 mb-md-0">
            <label class="font-weight-bold small text-uppercase text-muted">Format</label>
            <select v-model="format" class="form-control" style="border-radius:10px;">
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
          <div class="col-md-4 mb-2 mb-md-0">
            <label class="font-weight-bold small text-uppercase text-muted">Level</label>
            <select v-model="level" class="form-control" style="border-radius:10px;">
              <option value="novice">Novice</option>
              <option value="intermediate">Intermediate</option>
              <option value="open">Open</option>
            </select>
          </div>
          <div class="col-md-4 d-flex align-items-end">
            <button class="btn btn-primary btn-block py-2"
              @click="analyze"
              :disabled="!motionText.trim() || analyzing"
              style="border-radius:10px; font-weight:600; font-size:1rem;">
              <span v-if="analyzing" class="spinner-border spinner-border-sm mr-1" role="status"></span>
              {{ analyzing ? 'Analyzing...' : '🔍 Analyze Motion' }}
            </button>
          </div>
        </div>

        <!-- Pipeline Progress -->
        <div v-if="analyzing" class="mt-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <small class="text-muted font-weight-bold">Pipeline Progress</small>
            <small class="text-muted">{{ currentStage }}</small>
          </div>
          <div class="progress" style="height:6px; border-radius:3px;">
            <div class="progress-bar bg-primary" role="progressbar"
              :style="{ width: progressPercent + '%' }"
              style="transition: width 0.5s ease;"></div>
          </div>
          <div class="d-flex justify-content-between mt-2">
            <span v-for="(stage, i) in stages" :key="i"
              class="badge"
              :class="stageClass(i)">
              {{ stage }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== RESULTS ===== -->
    <div v-if="report" class="analysis-results">
      <!-- Meta Bar -->
      <div class="d-flex flex-wrap align-items-center justify-content-between mb-3 px-1">
        <div class="d-flex align-items-center flex-wrap">
          <span v-if="cached" class="badge badge-info mr-2">Cached</span>
          <span v-if="modelVersion" class="badge badge-secondary mr-2">{{ modelVersion }}</span>
          <span v-if="pipelineDuration" class="badge badge-light mr-2">{{ pipelineDuration }}ms</span>
          <span v-if="profile && profile.confidence" class="badge"
            :class="profile.confidence >= 0.7 ? 'badge-success' : profile.confidence >= 0.4 ? 'badge-warning' : 'badge-danger'">
            Confidence: {{ (profile.confidence * 100).toFixed(0) }}%
          </span>
        </div>
        <div v-if="profile && profile.motion_type" class="d-flex align-items-center">
          <span class="badge badge-primary mr-1">{{ profile.motion_type }}</span>
          <span class="badge badge-info mr-1" v-if="profile.domain_primary">{{ profile.domain_primary }}</span>
          <span class="badge badge-light" v-if="profile.requires_model">Model Required</span>
        </div>
      </div>

      <!-- Ambiguity Warning -->
      <div v-if="hasAmbiguity" class="alert alert-warning d-flex align-items-start mb-3" style="border-radius:10px;">
        <span class="mr-2" style="font-size:1.25rem">⚠️</span>
        <div>
          <strong>Ambiguity Detected</strong>
          <ul class="mb-0 mt-1 pl-3">
            <li v-for="(flag, i) in profile.ambiguity_flags" :key="'af-'+i">{{ flag }}</li>
          </ul>
        </div>
      </div>

      <!-- Quality / Specificity Warning -->
      <div v-if="report.quality_checks && report.quality_checks.specificity_score < 0.5"
        class="alert alert-info d-flex align-items-start mb-3" style="border-radius:10px;">
        <span class="mr-2" style="font-size:1.25rem">ℹ️</span>
        <div>
          <strong>Template-based analysis</strong> — AI service was unavailable.
          Analysis uses motion keywords but may lack deep specificity.
        </div>
      </div>

      <!-- TABS -->
      <ul class="nav nav-pills nav-fill mb-3 flex-nowrap overflow-auto" role="tablist"
        style="gap:4px; -webkit-overflow-scrolling:touch;">
        <li class="nav-item" v-for="(tab, i) in tabs" :key="'tab-'+i">
          <a class="nav-link px-3 py-2"
            :class="{ active: activeTab === tab.id }"
            @click.prevent="activeTab = tab.id"
            href="#"
            style="border-radius:8px; white-space:nowrap; font-size:0.85rem; font-weight:600;">
            {{ tab.icon }} {{ tab.label }}
          </a>
        </li>
      </ul>

      <!-- TAB: Quick Prep -->
      <div v-show="activeTab === 'quick'" class="tab-content-panel">
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">⚡ 30-Second Quick Prep</h5>
            <div class="row">
              <div class="col-md-8">
                <h6 class="text-primary font-weight-bold">Top 3 Clashes</h6>
                <div v-for="(clash, i) in topClashes" :key="'qc-'+i" class="mb-2">
                  <div class="d-flex align-items-start">
                    <span class="badge badge-primary mr-2 mt-1">{{ i + 1 }}</span>
                    <div>
                      <strong>{{ clash.axis }}</strong>
                      <div class="small text-muted mt-1">
                        <span class="text-success">Gov:</span> {{ clash.gov_claim }}
                        <br><span class="text-danger">Opp:</span> {{ clash.opp_claim }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-md-4">
                <h6 class="text-primary font-weight-bold">Best POIs</h6>
                <div v-for="(poi, i) in topPois" :key="'qp-'+i" class="mb-2 p-2 bg-light" style="border-radius:8px;">
                  <div class="small font-italic">"{{ poi.poi }}"</div>
                  <div class="small text-muted mt-1">Targets: {{ poi.targets }} · {{ poi.best_timing }}</div>
                </div>
                <h6 class="text-primary font-weight-bold mt-3">Framing</h6>
                <div v-if="report.weighing && report.weighing.length" class="small">
                  <div v-for="(w, i) in report.weighing.slice(0, 2)" :key="'qw-'+i" class="mb-1">
                    <span class="text-muted">📊</span> {{ w }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: Definitions -->
      <div v-show="activeTab === 'definitions'" class="tab-content-panel">
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">📖 Interpretations & Definitions</h5>
            <div v-for="(interp, i) in report.interpretations" :key="'int-'+i"
              class="mb-3 p-3" :class="i === 0 ? 'bg-light' : ''" style="border-radius:10px; border: 1px solid #e9ecef;">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0 font-weight-bold">{{ interp.title }}</h6>
                <span v-if="i === 0" class="badge badge-success">Most Standard</span>
                <span v-else class="badge badge-secondary">Alternative</span>
              </div>
              <p class="mb-1">{{ interp.definition }}</p>
              <small class="text-muted">{{ interp.fairness_notes }}</small>
            </div>
          </div>
        </div>

        <!-- Definition Traps -->
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">⚠️ Definition Traps</h5>
            <div v-for="(trap, i) in report.definition_traps" :key="'dt-'+i"
              class="mb-3 p-3 border-left border-warning" style="border-left-width:4px !important; background:#fffbf0; border-radius:0 10px 10px 0;">
              <div class="font-weight-bold text-danger mb-1">🚫 {{ trap.trap }}</div>
              <div class="small mb-1"><strong>Why it's bad:</strong> {{ trap.why_bad }}</div>
              <div class="small text-success"><strong>Fair line:</strong> {{ trap.fair_line }}</div>
            </div>
          </div>
        </div>

        <!-- Hidden Assumptions -->
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">🔍 Hidden Assumptions</h5>
            <ul class="mb-0 pl-3">
              <li v-for="(a, i) in report.hidden_assumptions" :key="'ha-'+i" class="mb-1">{{ a }}</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- TAB: Clash Map -->
      <div v-show="activeTab === 'clashes'" class="tab-content-panel">
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">⚔️ Clash Map</h5>
            <div v-for="(clash, i) in report.clash_areas" :key="'cm-'+i"
              class="mb-3 p-3" style="border-radius:10px; border: 1px solid #e2e8f0;">
              <div class="font-weight-bold mb-2" style="font-size:1.05rem;">
                <span class="badge badge-primary mr-1">{{ i + 1 }}</span>
                {{ clash.axis }}
              </div>
              <div class="row">
                <div class="col-md-6">
                  <div class="p-2" style="background:#e6f9e6; border-radius:8px;">
                    <div class="small font-weight-bold text-success mb-1">🟢 Government</div>
                    <div class="small">{{ clash.gov_claim }}</div>
                  </div>
                </div>
                <div class="col-md-6 mt-2 mt-md-0">
                  <div class="p-2" style="background:#ffe6e6; border-radius:8px;">
                    <div class="small font-weight-bold text-danger mb-1">🔴 Opposition</div>
                    <div class="small">{{ clash.opp_claim }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: Cases -->
      <div v-show="activeTab === 'cases'" class="tab-content-panel">
        <div class="row">
          <!-- Gov Model -->
          <div class="col-md-6 mb-3">
            <div class="card shadow-sm border-0 h-100" style="border-radius:12px; border-top:4px solid #28a745 !important;">
              <div class="card-body">
                <h5 class="font-weight-bold text-success mb-3">🟢 Government Case</h5>
                <div v-if="report.gov_model && report.gov_model.needed">
                  <h6 class="font-weight-bold">Model</h6>
                  <div class="mb-2">
                    <div class="small font-weight-bold text-muted">Mechanism:</div>
                    <ul class="pl-3 mb-1">
                      <li v-for="(m, i) in report.gov_model.mechanism" :key="'gm-'+i" class="small">{{ m }}</li>
                    </ul>
                  </div>
                  <div class="mb-2">
                    <div class="small font-weight-bold text-muted">Enforcement:</div>
                    <ul class="pl-3 mb-1">
                      <li v-for="(e, i) in report.gov_model.enforcement" :key="'ge-'+i" class="small">{{ e }}</li>
                    </ul>
                  </div>
                  <div>
                    <div class="small font-weight-bold text-muted">Success Metrics:</div>
                    <ul class="pl-3 mb-0">
                      <li v-for="(s, i) in report.gov_model.metrics_of_success" :key="'gs-'+i" class="small">{{ s }}</li>
                    </ul>
                  </div>
                </div>
                <div v-else class="text-muted small">
                  <em>No concrete model needed — this is a value/principle motion.</em>
                </div>
              </div>
            </div>
          </div>

          <!-- Opp Strategies -->
          <div class="col-md-6 mb-3">
            <div class="card shadow-sm border-0 h-100" style="border-radius:12px; border-top:4px solid #dc3545 !important;">
              <div class="card-body">
                <h5 class="font-weight-bold text-danger mb-3">🔴 Opposition Strategies</h5>
                <div v-for="(strat, i) in report.opp_strategies" :key="'os-'+i"
                  class="mb-3 p-2" style="background:#f8f9fa; border-radius:8px;">
                  <div class="d-flex align-items-center mb-1">
                    <strong>{{ strat.strategy }}</strong>
                    <span class="badge ml-2"
                      :class="{
                        'badge-info': strat.type === 'principled',
                        'badge-warning': strat.type === 'practical',
                        'badge-success': strat.type === 'alternative_model'
                      }">{{ strat.type }}</span>
                  </div>
                  <div class="small mb-1"><strong>How:</strong> {{ strat.how }}</div>
                  <div class="small text-muted"><strong>Impact:</strong> {{ strat.impact }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: Extensions -->
      <div v-show="activeTab === 'extensions'" class="tab-content-panel">
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">🔗 BP Extensions by Position</h5>
            <div class="row" v-if="report.extensions">
              <div class="col-md-6 mb-3" v-for="(role, key) in extensionRoles" :key="'ext-'+key">
                <div class="p-3 h-100" :style="{ background: role.bg, borderRadius: '10px', border: '1px solid ' + role.border }">
                  <div class="d-flex align-items-center mb-2">
                    <span class="mr-2" style="font-size:1.25rem;">{{ role.icon }}</span>
                    <strong>{{ role.label }}</strong>
                  </div>
                  <ul class="pl-3 mb-0 small" v-if="report.extensions[key]">
                    <li v-for="(ext, i) in report.extensions[key]" :key="'e-'+key+'-'+i" class="mb-1">{{ ext }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: POIs -->
      <div v-show="activeTab === 'pois'" class="tab-content-panel">
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">❓ Suggested POIs</h5>
            <div v-for="(poi, i) in report.pois" :key="'poi-'+i"
              class="mb-3 p-3 d-flex align-items-start" style="background:#f7f8fc; border-radius:10px; border:1px solid #e2e8f0;">
              <span class="badge badge-primary mr-3 mt-1" style="min-width:28px;">{{ i + 1 }}</span>
              <div class="flex-grow-1">
                <div class="font-italic mb-1" style="font-size:1.02rem;">"{{ poi.poi }}"</div>
                <div class="d-flex flex-wrap">
                  <span class="badge badge-light border mr-2">Targets: {{ poi.targets }}</span>
                  <span class="badge badge-light border">{{ poi.best_timing }}</span>
                </div>
              </div>
              <button class="btn btn-sm btn-outline-secondary ml-2" @click="copyText(poi.poi)" title="Copy POI">
                📋
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: Difficulty & Bias -->
      <div v-show="activeTab === 'metrics'" class="tab-content-panel">
        <div class="row">
          <!-- Difficulty -->
          <div class="col-md-6 mb-3">
            <div class="card shadow-sm border-0 h-100" style="border-radius:12px;">
              <div class="card-body">
                <h5 class="font-weight-bold mb-3">📈 Difficulty Assessment</h5>
                <div v-if="report.difficulty" class="mb-2">
                  <div v-for="(metric, key) in difficultyMetrics" :key="'dm-'+key" class="mb-3">
                    <div class="d-flex justify-content-between mb-1">
                      <span class="small font-weight-bold">{{ metric.label }}</span>
                      <span class="small text-muted">{{ report.difficulty[key] }}/10</span>
                    </div>
                    <div class="progress" style="height:8px; border-radius:4px;">
                      <div class="progress-bar" role="progressbar"
                        :style="{ width: (report.difficulty[key] * 10) + '%' }"
                        :class="barClass(report.difficulty[key])"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Bias -->
          <div class="col-md-6 mb-3">
            <div class="card shadow-sm border-0 h-100" style="border-radius:12px;">
              <div class="card-body">
                <h5 class="font-weight-bold mb-3">⚖️ Side Bias Analysis</h5>
                <div v-if="report.bias">
                  <div v-for="(metric, key) in biasMetrics" :key="'bm-'+key" class="mb-3">
                    <div class="d-flex justify-content-between mb-1">
                      <span class="small font-weight-bold">{{ metric.label }}</span>
                      <span class="small text-muted">{{ report.bias[key] }}/10</span>
                    </div>
                    <div class="progress" style="height:8px; border-radius:4px;">
                      <div class="progress-bar" role="progressbar"
                        :style="{ width: (report.bias[key] * 10) + '%' }"
                        :class="metric.barClass"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Weighing -->
        <div class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">📊 Weighing Framework</h5>
            <div class="row">
              <div v-for="(w, i) in report.weighing" :key="'wf-'+i" class="col-md-6 mb-2">
                <div class="p-2 bg-light d-flex align-items-start" style="border-radius:8px;">
                  <span class="badge badge-primary mr-2 mt-1">{{ i + 1 }}</span>
                  <span class="small">{{ w }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quality Checks -->
        <div v-if="report.quality_checks" class="card shadow-sm border-0 mb-3" style="border-radius:12px;">
          <div class="card-body">
            <h5 class="font-weight-bold mb-3">✅ Quality Check</h5>
            <div class="d-flex flex-wrap mb-2">
              <span class="badge mr-2 mb-1"
                :class="report.quality_checks.specificity_score >= 0.7 ? 'badge-success' : 'badge-warning'">
                Specificity: {{ (report.quality_checks.specificity_score * 100).toFixed(0) }}%
              </span>
              <span class="badge mr-2 mb-1"
                :class="{
                  'badge-success': report.quality_checks.hallucination_risk === 'low',
                  'badge-warning': report.quality_checks.hallucination_risk === 'medium',
                  'badge-danger': report.quality_checks.hallucination_risk === 'high'
                }">
                Hallucination Risk: {{ report.quality_checks.hallucination_risk }}
              </span>
            </div>
            <ul v-if="report.quality_checks.notes" class="pl-3 mb-0 small text-muted">
              <li v-for="(note, i) in report.quality_checks.notes" :key="'qn-'+i">{{ note }}</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- ===== FEEDBACK BAR ===== -->
      <div class="card shadow-sm border-0 mt-3" style="border-radius:12px;">
        <div class="card-body py-3">
          <div class="d-flex flex-wrap align-items-center justify-content-between">
            <div class="d-flex align-items-center">
              <span class="mr-2 small font-weight-bold text-muted">Was this helpful?</span>
              <button v-for="n in 5" :key="'star-'+n"
                class="btn btn-sm p-0 mr-1"
                :class="feedbackRating >= n ? 'text-warning' : 'text-muted'"
                @click="feedbackRating = n"
                style="font-size:1.25rem; line-height:1;">
                ★
              </button>
            </div>
            <div class="d-flex flex-wrap mt-2 mt-md-0">
              <button class="btn btn-sm mr-1 mb-1"
                :class="feedbackSpecific ? 'btn-success' : 'btn-outline-secondary'"
                @click="feedbackSpecific = !feedbackSpecific">
                Motion-specific?
              </button>
              <button class="btn btn-sm mr-1 mb-1"
                :class="feedbackFair ? 'btn-success' : 'btn-outline-secondary'"
                @click="feedbackFair = !feedbackFair">
                Fair & balanced?
              </button>
              <button class="btn btn-sm mr-1 mb-1"
                :class="feedbackHelpful ? 'btn-success' : 'btn-outline-secondary'"
                @click="feedbackHelpful = !feedbackHelpful">
                Actually helpful?
              </button>
              <button v-if="feedbackRating > 0" class="btn btn-sm btn-primary mb-1"
                @click="submitFeedback" :disabled="feedbackSubmitted">
                {{ feedbackSubmitted ? '✓ Sent' : 'Submit' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="alert alert-danger mt-3" style="border-radius:10px;">
      <strong>Error:</strong> {{ error }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'MotionDoctor',
  data () {
    return {
      // Input
      motionText: '',
      format: 'bp',
      infoSlide: '',
      level: 'open',

      // State
      analyzing: false,
      error: null,
      currentStageIndex: -1,

      // Results
      report: null,
      profile: null,
      plan: null,
      validationLog: [],
      reportId: null,
      modelVersion: '',
      pipelineDuration: null,
      cached: false,

      // UI
      activeTab: 'quick',

      // Feedback
      feedbackRating: 0,
      feedbackSpecific: false,
      feedbackFair: false,
      feedbackHelpful: false,
      feedbackSubmitted: false,

      // Constants
      stages: ['Profiling', 'Planning', 'Generating', 'Validating'],
      tabs: [
        { id: 'quick', icon: '⚡', label: 'Quick Prep' },
        { id: 'definitions', icon: '📖', label: 'Definitions' },
        { id: 'clashes', icon: '⚔️', label: 'Clash Map' },
        { id: 'cases', icon: '📋', label: 'Cases' },
        { id: 'extensions', icon: '🔗', label: 'Extensions' },
        { id: 'pois', icon: '❓', label: 'POIs' },
        { id: 'metrics', icon: '📊', label: 'Metrics' },
      ],
      extensionRoles: {
        OG: { label: 'Opening Government', icon: '🟢', bg: '#e6f9e6', border: '#b7e4b7' },
        OO: { label: 'Opening Opposition', icon: '🔴', bg: '#ffe6e6', border: '#f5b7b7' },
        CG: { label: 'Closing Government', icon: '🟩', bg: '#e6f0ff', border: '#b7d1f5' },
        CO: { label: 'Closing Opposition', icon: '🟥', bg: '#fff0e6', border: '#f5d4b7' },
      },
      difficultyMetrics: {
        complexity: { label: 'Overall Complexity' },
        tech_knowledge: { label: 'Technical Knowledge Required' },
        abstraction: { label: 'Abstraction Level' },
      },
      biasMetrics: {
        burden_gov: { label: 'Gov Burden', barClass: 'bg-success' },
        burden_opp: { label: 'Opp Burden', barClass: 'bg-danger' },
        ground_gov: { label: 'Gov Ground', barClass: 'bg-success' },
        ground_opp: { label: 'Opp Ground', barClass: 'bg-danger' },
      },
    }
  },
  computed: {
    progressPercent () {
      if (this.currentStageIndex < 0) return 0
      return Math.min(100, ((this.currentStageIndex + 1) / this.stages.length) * 100)
    },
    currentStage () {
      if (this.currentStageIndex < 0 || this.currentStageIndex >= this.stages.length) return ''
      return this.stages[this.currentStageIndex]
    },
    hasAmbiguity () {
      return this.profile && this.profile.ambiguity_flags && this.profile.ambiguity_flags.length > 0
    },
    topClashes () {
      if (!this.report || !this.report.clash_areas) return []
      return this.report.clash_areas.slice(0, 3)
    },
    topPois () {
      if (!this.report || !this.report.pois) return []
      return this.report.pois.slice(0, 2)
    },
  },
  methods: {
    stageClass (index) {
      if (this.currentStageIndex > index) return 'badge-success'
      if (this.currentStageIndex === index) return 'badge-primary'
      return 'badge-light'
    },
    barClass (value) {
      if (value <= 3) return 'bg-success'
      if (value <= 6) return 'bg-warning'
      return 'bg-danger'
    },

    async analyze () {
      this.analyzing = true
      this.error = null
      this.report = null
      this.profile = null
      this.plan = null
      this.cached = false
      this.feedbackRating = 0
      this.feedbackSpecific = false
      this.feedbackFair = false
      this.feedbackHelpful = false
      this.feedbackSubmitted = false

      // Simulate pipeline progress
      this.currentStageIndex = 0
      const progressInterval = setInterval(() => {
        if (this.currentStageIndex < this.stages.length - 1) {
          this.currentStageIndex++
        }
      }, 2500)

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
            format: this.format,
            info_slide: this.infoSlide || undefined,
            level: this.level,
          }),
        })
        if (!response.ok) throw new Error('Analysis failed — server returned ' + response.status)
        const data = await response.json()

        this.report = data.report || data.analysis || data
        this.profile = data.profile || {}
        this.plan = data.plan || {}
        this.validationLog = data.validation_log || []
        this.reportId = data.report_id || null
        this.modelVersion = data.model_version || ''
        this.pipelineDuration = data.pipeline_duration_ms || null
        this.cached = data.cached || false
        this.activeTab = 'quick'
      } catch (e) {
        this.error = 'Failed to analyze motion. Please try again.'
        console.error(e)
      }

      clearInterval(progressInterval)
      this.currentStageIndex = this.stages.length
      this.analyzing = false
    },

    async submitFeedback () {
      if (!this.reportId || this.feedbackSubmitted) return
      try {
        const config = window.motionDoctorConfig || {}
        const baseUrl = config.analyzeUrl || '/motions-bank/api/doctor/analyze/'
        const feedbackUrl = baseUrl.replace('analyze/', 'feedback/')
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
          document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1]

        await fetch(feedbackUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            report: this.reportId,
            rating: this.feedbackRating,
            was_specific: this.feedbackSpecific,
            was_fair: this.feedbackFair,
            was_helpful: this.feedbackHelpful,
          }),
        })
        this.feedbackSubmitted = true
      } catch (e) {
        console.error('Feedback submission failed:', e)
      }
    },

    copyText (text) {
      navigator.clipboard.writeText(text).then(() => {
        // Could add a toast notification here
      }).catch(err => console.error('Copy failed:', err))
    },
  },
}
</script>
