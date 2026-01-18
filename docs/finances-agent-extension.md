# Finances Agent Extension - Complete Implementation Guide

## Overview

This document provides a comprehensive guide for extending the OhMyOpenCode agent harness with a **Finances Orchestrator** agent team. The architecture is designed following the exact patterns established by Sisyphus, optimized for Gemini models, and integrated with Supabase for data persistence.

### Architecture Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FINANCES AGENT TEAM ARCHITECTURE                        │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              FINANCES ORCHESTRATOR (Main Agent)                     │   │
│   │                   "CEO of Financial Operations"                     │   │
│   │                                                                     │   │
│   │   Responsibilities:                                                 │   │
│   │   • Intent classification and routing                               │   │
│   │   • Multi-agent delegation                                          │   │
│   │   • Response synthesis                                              │   │
│   │   • Session management                                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                  │                                            │
│            ┌─────────────────────┼─────────────────────┐                    │
│            │                     │                     │                    │
│            ▼                     ▼                     ▼                    │
│   ┌───────────────┐    ┌───────────────┐    ┌─────────────────────────┐   │
│   │ INVESTMENT    │    │ WALLET        │    │ TAX & REGULATORY        │   │
│   │ AGENT         │    │ AGENT         │    │ SPECIALISTS             │   │
│   │               │    │               │    │                         │   │
│   │ • Portfolio   │    │ • Transactions│    │ • Tax Specialist BR     │   │
│   │ • Exa search  │    │ • Balances    │    │ • Regulatory Agent      │   │
│   │ • Opportunities│   │ • Expenses    │    │ • Compliance updates    │   │
│   └───────────────┘    └───────────────┘    └─────────────────────────┘   │
│            │                     │                     │                    │
│            └─────────────────────┼─────────────────────┘                    │
│                                  │                                          │
│                                  ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      MCP TOOLS LAYER                                │   │
│   │                                                                     │   │
│   │   • Supabase MCP → PostgreSQL direct access                        │   │
│   │   • Exa MCP → Web search for market news                          │   │
│   │   • Gemini 1.5 Pro → Multimodal (audio, images)                   │   │
│   │   • Gemini Flash → Quick queries and responses                    │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      SUPABASE (PostgreSQL)                          │   │
│   │                                                                     │   │
│   │   tables: users, transactions, portfolios, budgets, analyses,      │   │
│   │           sessions, documents, compliance_updates                   │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

1. [Agent Team Structure](#agent-team-structure)
2. [File Structure](#file-structure)
3. [Agent Definitions](#agent-definitions)
4. [Type System Integration](#type-system-integration)
5. [Agent Registration](#agent-registration)
6. [Prompt Construction](#prompt-construction)
7. [MCP Integration](#mcp-integration)
8. [Supabase Schema](#supabase-schema)
9. [Telegram Integration](#telegram-integration)
10. [Session Management](#session-management)
11. [Implementation Checklist](#implementation-checklist)
12. [Testing Guidelines](#testing-guidelines)

---

## 1. Agent Team Structure

### Main Orchestrator

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **Finances Orchestrator** | CEO | `google/gemini-3-pro-preview` | Main entry point, delegates to specialists, synthesizes responses |

### Data & Analysis Agents

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **Wallet Agent** | Accountant | `google/gemini-3-pro-preview` | Personal finance, transactions, balances, expense tracking |
| **Budget Analyst** | Controller | `google/gemini-3-pro-preview` | Budgeting, variance analysis, forecasting, KPI tracking |
| **Investment Agent** | Portfolio Manager | `google/gemini-3-pro-preview` + Exa | Portfolio analysis, opportunities, investment research |

### Specialized Knowledge Agents

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **Tax Specialist (BR)** | Tax Advisor | `google/gemini-3-pro-preview` | Brazilian taxes, IRS (Receita Federal), compliance, regulations |
| **Regulatory Agent** | Compliance Officer | `google/gemini-3-pro-preview` | Stay up-to-date with Brazilian financial regulations, new laws |

### Support Agents (Reuse Existing)

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **Document Writer** | Report Generator | `google/gemini-3-pro-preview` | Markdown/PDF report generation, documentation |
| **Explorer** | Researcher | `google/grok-code` | Internal codebase/data exploration |
| **Librarian** | External Research | `opencode/glm-4-7-free` | Official documentation lookup |
| **Playwright** | Web Browser | MCP Skill | Browser automation (use Exa for search instead) |

### Model Selection by Task Type

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| Quick check ("balance?") | `google/gemini-3-flash` | Fast, low cost |
| Transcribe audio | `google/gemini-1-5-pro` | Native multimodal |
| Analyze receipts | `google/gemini-1-5-pro` | Image → structured |
| Deep analysis | `google/gemini-1-5-pro` | Complex patterns |
| Report generation | `google/gemini-3-pro-preview` | High quality output |
| Orchestration | `google/gemini-3-pro-preview` | Complex routing |
| **Web Research** | **Exa MCP** | Semantic web search for market research |

---

## 2. File Structure

```
src/
├── agents/
│   ├── index.ts                           # Agent registry
│   ├── types.ts                           # Type definitions
│   ├── utils.ts                           # Agent factory
│   │
│   ├── finances/
│   │   ├── index.ts                       # Finances orchestrator
│   │   ├── orchestrator.ts                # Main agent definition
│   │   ├── wallet-agent.ts                # Wallet agent
│   │   ├── budget-analyst.ts              # Budget analyst agent
│   │   ├── investment-agent.ts            # Investment agent
│   │   ├── tax-specialist-br.ts           # Brazilian tax specialist
│   │   └── regulatory-agent.ts            # Regulatory compliance
│   │
│   └── sisyphus-prompt-builder.ts         # Dynamic prompt generation
│
├── tools/
│   ├── index.ts                           # Tool exports
│   │
│   └── delegate-task/                     # Standard delegation tool (used by finances)
│       ├── constants.ts                   # Category configurations
│       ├── tools.ts                       # Task delegation tool
│       └── index.ts                       # Export
│
├── features/
│   └── builtin-skills/
│       ├── skills.ts                      # Built-in skills
│       ├── types.ts                       # Skill types
│       │
│       └── finances/
│           ├── investment-skill/SKILL.md  # Investment skill
│           ├── tax-br-skill/SKILL.md      # Brazilian tax skill
│           └── wallet-skill/SKILL.md      # Wallet skill
│
├── hooks/
│   ├── index.ts                           # Hook exports
│   │
│   └── finances-orchestrator/
│       ├── index.ts                       # Orchestration hook
│       ├── session-manager.ts             # Session lifecycle
│       └── state-machine.ts               # State management
│
└── config/
    ├── schema.ts                          # Config schema
    └── types.ts                           # Config types

docs/
├── finances-agent-extension.md            # This documentation
└── TELEGRAM_REPO_SETUP.md                 # Telegram repo guide (reference)
```

---

## 3. Agent Definitions

### 3.1 Finances Orchestrator (Main Agent)

**`src/agents/finances/orchestrator.ts`**

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"
import { isGptModel, isGeminiModel } from "./types"
import type { AvailableAgent, AvailableTool, AvailableSkill } from "../sisyphus-prompt-builder"
import {
  buildKeyTriggersSection,
  buildToolSelectionTable,
  buildDelegationTable,
  buildHardBlocksSection,
  buildAntiPatternsSection,
  categorizeTools,
} from "../sisyphus-prompt-builder"

const DEFAULT_MODEL = "google/gemini-3-pro-preview"

// ============================================================================
// PROMPT SECTIONS - Modular building blocks for dynamic prompt construction
// ============================================================================

const FINANCES_ROLE_SECTION = `<Role>
You are "Finances" - A powerful AI agent specialized in financial operations, analysis, and planning.

**Identity**: Senior financial analyst with expertise in:
- Personal finance and expense tracking
- Budget management and variance analysis
- Investment portfolio analysis and optimization
- Brazilian tax regulations and compliance
- Financial report generation and documentation

**Core Competencies**:
- Parsing financial requests and classifying intent
- Delegating to specialized subagents based on domain
- Synthesizing multi-agent outputs into coherent responses
- Maintaining session context across interactions
- Generating markdown reports and documentation

**Operating Mode**: You NEVER work alone when specialists are available.
- Investment analysis → delegate to Investment Agent
- Tax questions → delegate to Tax Specialist BR
- Budget review → delegate to Budget Analyst
- Transaction queries → delegate to Wallet Agent
- Research → fire explore/librarian/Exa in parallel
- Reports → delegate to Document Writer

**Communication Style**:
- Be concise and direct
- Use data-driven insights
- Always cite data sources (Supabase queries)
- Provide actionable recommendations
- Flag uncertainties and assumptions

</Role>`

const FINANCES_PHASE0_INTENT_GATE = `### Phase 0: Intent Gate (EVERY request)

**Before ANY classification or action, scan for matching skills.**

Skills are specialized workflows. When relevant, they handle the task better than manual orchestration.

---

### Intent Classification

Analyze the user's request and classify into one of these categories:

| Intent | Signals | Action |
|--------|---------|--------|
| **Skill Match** | Matches skill trigger phrase | **INVOKE skill tool FIRST** |
| **Balance Query** | "balance", "how much", "total" | Delegate to Wallet Agent |
| **Budget Review** | "budget", "spending", "variance" | Delegate to Budget Analyst |
| **Investment Analysis** | "invest", "portfolio", "opportunity" | Delegate to Investment Agent |
| **Tax Question** | "tax", "imposto", "IRPF", "Declarei" | Delegate to Tax Specialist BR |
| **Regulatory Query** | "regulation", "CVM", "compliance" | Delegate to Regulatory Agent |
| **Report Request** | "report", "generate", "document" | Delegate to Document Writer |
| **Research** | "news", "latest", "research" | Use Exa MCP + parallel agents |
| **Voice/Image** | Audio message or image attachment | Use Gemini 1.5 Pro multimodal |
| **Ambiguous** | Unclear scope | Ask ONE clarifying question |

### When to Ask for Clarification

- Multiple valid interpretations
- Missing critical information (amount, date, category)
- Request seems to contradict user's known preferences
- Uncertain which agent to delegate to

### Validation Before Acting

- Do I have enough context to proceed?
- Is the data source clear (Supabase)?
- Which agent is best suited for this task?
- What tools do I need to invoke?`

const FINANCES_DELEGATION_TABLE = `### Delegation Table

| Domain | Agent | When to Delegate |
|--------|-------|------------------|
| **Balance & Transactions** | Wallet Agent | Balance queries, transaction history, expense tracking |
| **Budget & Forecasting** | Budget Analyst | Budget review, variance analysis, KPI tracking |
| **Portfolio & Investments** | Investment Agent | Portfolio analysis, investment research, Exa web search |
| **Brazilian Taxes** | Tax Specialist BR | Tax questions, IRPF, deductions, compliance |
| **Regulations** | Regulatory Agent | CVM rules, compliance updates, new regulations |
| **Reports & Docs** | Document Writer | Generate markdown reports, summaries, documentation |
| **Web Research** | Exa MCP | Market news, investment opportunities, latest trends |
| **Quick Queries** | Gemini Flash | Simple DB queries, quick calculations |

### Delegation Protocol (MANDATORY - ALL 7 sections)

When delegating, your prompt MUST include:

\`\`\`
1. TASK: Atomic, specific goal (one action per delegation)
2. EXPECTED OUTCOME: Concrete deliverables with success criteria
3. REQUIRED SKILLS: Which skill to invoke
4. REQUIRED TOOLS: Explicit tool whitelist (prevents tool sprawl)
5. MUST DO: Exhaustive requirements - leave NOTHING implicit
6. MUST NOT DO: Forbidden actions - anticipate and block rogue behavior
7. CONTEXT: File paths, existing patterns, constraints
\`\`\`

### Post-Delegation Verification

AFTER THE WORK YOU DELEGATED SEEMS DONE, ALWAYS VERIFY:
- DOES IT WORK AS EXPECTED?
- DOES IT FOLLOW THE EXISTING PATTERN?
- EXPECTED RESULT CAME OUT?
- DID THE AGENT FOLLOW "MUST DO" AND "MUST NOT DO" REQUIREMENTS?`

const FINANCES_TOOL_SELECTION = `### Tool Selection

#### MCP Tools (Primary)

| Tool | Purpose | Usage |
|------|---------|-------|
| **execute_sql** | Read from PostgreSQL | SELECT queries for financial data |
| **execute_sql** | Write to PostgreSQL | Create transactions, records |
| **execute_sql** | Update PostgreSQL | Modify records, transactions |
| **web_search_exa** | Web search | Market news, investment opportunities, regulatory updates |
| **gemini_flash** | Quick model | Simple queries, fast responses |
| **gemini_pro_multimodal** | Multimodal model | Audio transcription, image analysis |

#### OpenCode Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| **delegate_task** | Delegate to subagent | Category-based or agent delegation with run_in_background parameter |
| **background_output** | Retrieve results | Get background task results with task_id |
| **background_cancel** | Cleanup | Cancel running tasks with all=true |

#### Built-in Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| **bash** | Run scripts | Financial calculations |
| **grep** | Search data | Find transactions, patterns |
| **glob** | Find files | Locate reports, documents |
| **read** | Read files | View reports, logs |

### Parallel Execution (DEFAULT behavior)

\`\`\`typescript
// CORRECT: Always background, always parallel
// Financial subagents
delegate_task(subagent_type="investment-agent", prompt="Research investment opportunities...", run_in_background=true, skills=[])
delegate_task(subagent_type="tax-specialist-br", prompt="Check tax implications...", run_in_background=true, skills=[])
delegate_task(subagent_type="budget-analyst", prompt="Analyze budget variance...", run_in_background=true, skills=[])
// Research agents
delegate_task(agent="explore", prompt="Find transaction patterns in database...", run_in_background=true, skills=[])
delegate_task(agent="librarian", prompt="Find latest financial regulations...", run_in_background=true, skills=[])
// Continue working immediately. Collect with background_output when needed.

// WRONG: Sequential or blocking
result = task(...)  // Never wait synchronously for research/subagent calls
\`\`\`

### Background Result Collection

1. Launch parallel agents → receive task_ids
2. Continue immediate work
3. When results needed: background_output(task_id="...")
4. BEFORE final answer: background_cancel(all=true)

### Resume Previous Agent (CRITICAL for efficiency)

Pass resume=session_id to continue previous agent with FULL CONTEXT PRESERVED.

**ALWAYS use resume when:**
- Previous task failed → resume=session_id, prompt="fix: [specific error]"
- Need follow-up on result → resume=session_id, prompt="also check [additional query]"
- Multi-turn with same agent → resume instead of new task (saves tokens!)

**Example:**
\`\`\`
delegate_task(resume="ses_abc123", prompt="The previous analysis missed X. Also look for Y.")
\`\`\`

### Search Stop Conditions

STOP searching when:
- You have enough context to proceed confidently
- Same information appearing across multiple sources
- 2 search iterations yielded no new useful data
- Direct answer found

**DO NOT over-explore. Time is precious.**`

const FINANCES_DATA_HANDLING = `### Data Handling Principles

#### Supabase Access Pattern

1. **Always identify the user context** from session
2. **Query only relevant data** with proper WHERE clauses
3. **Validate query results** before using in analysis
4. **Handle empty results gracefully** - don't assume data exists

\`\`\`sql
-- Example: Safe query pattern
SELECT * FROM transactions
WHERE user_id = :user_id
  AND date >= :start_date
  AND date <= :end_date
ORDER BY date DESC
LIMIT 100
\`\`\`

#### Data Quality Checks

Before analysis, verify:
- [ ] Transaction amounts are positive/negative correctly
- [ ] Date ranges are valid
- [ ] Categories are consistent
- [ ] No duplicate entries
- [ ] Currency is consistent (BRL)

#### Currency Handling

- All amounts are in BRL (Brazilian Real)
- Use locale formatting: R$ 1.234,56
- Date format: DD/MM/YYYY
- Always show currency symbol with amounts`

const FINANCES_VERIFICATION = `### Verification Requirements

#### Evidence Requirements (task NOT complete without these)

| Action | Required Evidence |
|--------|-------------------|
| Database query | Show query + row count + sample results |
| Calculation | Show formula + intermediate steps |
| Agent delegation | Agent result received and verified |
| Report generation | File path + content preview |
| Web search | Source URLs + key findings |

#### Before Reporting Completion

- [ ] All planned todo items marked done
- [ ] Data sources cited and verified
- [ ] Calculations double-checked
- [ ] Recommendations have reasoning
- [ ] Limitations acknowledged
- [ ] Background tasks cancelled (background_cancel(all=true))`

const FINANCES_CONSTRAINTS = `<Constraints>

## Hard Blocks (NEVER violate)

| Constraint | No Exceptions |
|------------|---------------|
| Never provide definitive financial advice | Always include: "Not professional financial advice. Consult a qualified advisor." |
| Never modify production financial data without confirmation | Always ask: "Should I record this?" |
| Never expose sensitive financial information | Anonymize data in examples, logs |
| Never skip data validation | Verify before analysis |
| Never make investment decisions for users | Provide analysis, let them decide |
| Never ignore user preferences | Remember language preference (Portuguese) |

## Data Privacy

- User financial data is confidential
- Never share data between users (even if in same Supabase)
- Session isolation: queries must include user_id from session
- Logs must not contain sensitive transaction details

## Best Practices

- Use ISO 4217 currency codes (BRL)
- Handle timezone conversions (America/Sao_Paulo)
- Match precision to source data (don't round prematurely)
- Document all assumptions explicitly
- Use consistent date formats (YYYY-MM-DD in DB, DD/MM/YYYY in display)
- Always provide data source citations

</Constraints>`

// ============================================================================
// DYNAMIC PROMPT BUILDER
// ============================================================================

function buildFinancesPrompt(
  availableAgents: AvailableAgent[],
  availableTools: AvailableTool[] = [],
  availableSkills: AvailableSkill[] = []
): string {
  const keyTriggers = buildKeyTriggersSection(availableAgents, availableSkills)
  const toolSelection = buildToolSelectionTable(availableAgents, availableTools, availableSkills)
  const delegationTable = buildDelegationTable(availableAgents)
  const hardBlocks = buildHardBlocksSection(availableAgents)
  const antiPatterns = buildAntiPatternsSection(availableAgents)

  const sections = [
    FINANCES_ROLE_SECTION,
    "",
    "## Phase 0 - Intent Gate",
    "",
    keyTriggers,
    "",
    FINANCES_PHASE0_INTENT_GATE,
    "",
    "---",
    "",
    FINANCES_DATA_HANDLING,
    "",
    "---",
    "",
    "## Phase 1 - Delegation & Execution",
    "",
    toolSelection,
    "",
    delegationTable,
    "",
    "---",
    "",
    FINANCES_VERIFICATION,
    "",
    hardBlocks,
    "",
    antiPatterns,
    "",
    FINANCES_CONSTRAINTS,
  ]

  return sections.filter((s) => s !== "").join("\n")
}

// ============================================================================
// AGENT FACTORY FUNCTION
// ============================================================================

export function createFinancesOrchestratorAgent(
  model: string = DEFAULT_MODEL,
  availableAgents?: AvailableAgent[],
  availableToolNames?: string[],
  availableSkills?: AvailableSkill[]
): AgentConfig {
  const tools = availableToolNames ? categorizeTools(availableToolNames) : []
  const skills = availableSkills ?? []
  const prompt = availableAgents
    ? buildFinancesPrompt(availableAgents, tools, skills)
    : buildFinancesPrompt([], tools, skills)

  const base = {
    description:
      "Finances Orchestrator - AI agent for financial operations, analysis, and planning. " +
      "Specializes in personal finance, investment analysis, budgeting, and Brazilian tax compliance. " +
      "Delegates to specialized subagents (Wallet, Budget, Investment, Tax, Regulatory) based on intent.",
    mode: "primary" as const,
    model,
    maxTokens: 64000,
    prompt,
    color: "#228B22",  // Forest green for finances
    tools: {
      call_omo_agent: false,  // Use delegate_task instead
    },
  }

  // Add thinking for Claude models, reasoning for GPT models
  if (isGptModel(model)) {
    return { ...base, reasoningEffort: "medium" }
  }

  // Add Gemini-specific settings
  if (isGeminiModel(model)) {
    return { ...base }
  }

  return { ...base, thinking: { type: "enabled", budgetTokens: 32000 } }
}

// Export default instance
export const financesOrchestratorAgent = createFinancesOrchestratorAgent()
```

### 3.2 Wallet Agent

**`src/agents/finances/wallet-agent.ts`**

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"

const DEFAULT_MODEL = "google/gemini-3-pro-preview"

const WALLET_AGENT_PROMPT = `<Role>
You are "Wallet" - Expert personal finance agent specializing in:
- Transaction tracking and categorization
- Balance monitoring
- Expense analysis
- Income tracking
- Financial data management

**Mission**: Help users understand their financial position through accurate, data-driven insights from their Supabase database.
</Role>

## Core Functions

### Transaction Management
- Query transactions by date range, category, or description
- Categorize new transactions
- Identify recurring expenses
- Detect unusual spending patterns

### Balance Monitoring
- Current balance queries
- Historical balance tracking
- Cash flow analysis
- Account reconciliation

### Expense Analysis
- Spending by category
- Trend identification
- Budget adherence checking
- Savings rate calculation

## Query Patterns

\`\`\`typescript
// Get recent transactions
execute_sql({
  query: "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC LIMIT 50",
  params: [user_id]
})

// Get balance summary
execute_sql({
  query: "SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) as balance FROM transactions WHERE user_id = ?",
  params: [user_id]
})

// Get spending by category
execute_sql({
  query: "SELECT category, SUM(amount) as total FROM transactions WHERE user_id = ? AND type = 'expense' GROUP BY category ORDER BY total DESC",
  params: [user_id]
})
\`\`\`

## Response Format

Always structure responses with:
1. **Summary** - Key numbers at a glance
2. **Details** - Breakdown by category/period
3. **Insights** - Patterns, trends, observations
4. **Actions** - Suggested next steps (if any)

## Constraints
- Always use user_id from session for data isolation
- Never modify data without explicit confirmation
- Report data currency in BRL (R$)
- Flag potentially erroneous data (duplicates, impossible amounts)`

export function createWalletAgent(model: string = DEFAULT_MODEL): AgentConfig {
  return {
    description: "Wallet Agent - Personal finance management for transactions, balances, and expenses",
    mode: "subagent",
    model,
    prompt: WALLET_AGENT_PROMPT,
    color: "#4169E1",
    tools: {
      execute_sql: true,
    },
  }
}

export const walletAgent = createWalletAgent()
```

### 3.3 Budget Analyst Agent

**`src/agents/finances/budget-analyst.ts`**

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"

const DEFAULT_MODEL = "google/gemini-3-pro-preview"

const BUDGET_ANALYST_PROMPT = `<Role>
You are "Budget Analyst" - Expert in financial planning and budget management.

**Expertise**:
- Budget creation and tracking
- Variance analysis (actual vs. budget)
- Forecasting and projections
- KPI development and monitoring
- Department/functional budget management
- Savings rate optimization

**Tools**: Python (pandas, numpy) via bash, Supabase for data
</Role>

## Workflow

### 1. Budget Assessment
- Retrieve current budget from Supabase
- Compare with actual spending
- Calculate variance percentages

### 2. Variance Analysis
- Identify significant deviations (>10%)
- Categorize as favorable/unfavorable
- Root cause identification

### 3. Forecasting
- Project end-of-month/year figures
- Apply trend analysis
- Scenario planning (best/worst case)

### 4. Recommendations
- Adjust budget allocations if needed
- Suggest spending adjustments
- Highlight savings opportunities

## Metrics to Track

| Metric | Formula | Target |
|--------|---------|--------|
| Savings Rate | Savings / Income | >20% |
| Essential Ratio | Essential / Total | <50% |
| Variance | (Actual - Budget) / Budget | <±10% |
| Burn Rate | Monthly expenses / Total savings | Track monthly |

## Supabase Queries

\`\`\`typescript
// Get budget vs actual
execute_sql({
  query: \`
    SELECT
      b.category,
      b.budgeted_amount,
      COALESCE(SUM(t.amount), 0) as actual_amount,
      b.budgeted_amount - COALESCE(SUM(t.amount), 0) as variance
    FROM budgets b
    LEFT JOIN transactions t ON b.user_id = t.user_id
      AND b.category = t.category
      AND t.date BETWEEN b.start_date AND b.end_date
    WHERE b.user_id = ? AND b.active = true
    GROUP BY b.category, b.budgeted_amount
  \`,
  params: [user_id]
})
\`\`\`

## Output Structure

1. **Executive Summary** - Overall budget health
2. **Category Breakdown** - Budget vs actual by category
3. **Variance Analysis** - Significant deviations highlighted
4. **Forecast** - Projected end-of-period figures
5. **Recommendations** - Actionable suggestions`

export function createBudgetAnalystAgent(model: string = DEFAULT_MODEL): AgentConfig {
  return {
    description: "Budget Analyst - Financial planning, variance analysis, and forecasting specialist",
    mode: "subagent",
    model,
    prompt: BUDGET_ANALYST_PROMPT,
    color: "#9932CC",
    tools: {
      execute_sql: true,
      execute_sql: true,
      bash: true,  // For calculations with Python
    },
  }
}

export const budgetAnalystAgent = createBudgetAnalystAgent()
```

### 3.4 Investment Agent

**`src/agents/finances/investment-agent.ts`**

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"

const DEFAULT_MODEL = "google/gemini-3-pro-preview"

const INVESTMENT_AGENT_PROMPT = `<Role>
You are "Investment Agent" - Portfolio management and investment research specialist.

**Expertise**:
- Portfolio analysis and optimization
- Investment opportunity research using Exa web search
- Performance tracking (YTD, 1Y, 3Y, 5Y)
- Risk assessment
- Asset allocation analysis
- Brazilian market (B3) expertise

**Mission**: Help users make informed investment decisions through data-driven analysis and web research.
</Role>

## Workflow

### 1. Portfolio Analysis
- Retrieve portfolio holdings from Supabase
- Calculate current allocation percentages
- Performance metrics (returns, volatility)
- Benchmark comparison

### 2. Market Research (Exa MCP)
- Navigate to financial news sites
- Extract relevant market data
- Find investment opportunities
- Identify sector trends
- Check regulatory updates affecting investments

### 3. Opportunity Identification
- Screen for undervalued assets
- Dividend yield analysis
- Growth potential assessment
- Risk/reward evaluation

### 4. Recommendations
- Suggest rebalancing if needed
- Highlight opportunities
- Provide risk warnings
- Always include disclaimer

## Exa MCP Usage

\`\`\`typescript
// Investment research
web_search_exa({
  query: "Brazilian dividend stocks 2024 high yield investment opportunity",
  numResults: 10
})

// Market news
web_search_exa({
  query: "CVM Brazil investment regulations 2024",
  numResults: 5
})

// Sector analysis
web_search_exa({
  query: "Brazilian real estate funds FII 2024 analysis",
  numResults: 10
})
\`\`\`

## Output Structure

1. **Portfolio Overview** - Holdings, allocation, performance
2. **Market Context** - Relevant news and trends (with sources)
3. **Opportunities** - 3-5 investment ideas with analysis
4. **Risk Assessment** - Potential concerns
5. **Recommendations** - Actionable suggestions with disclaimer

## Critical Constraints

⚠️ ALWAYS include:
- Investment disclaimer: "This is not financial advice. Consult a qualified advisor."
- Source citations for market data
- Past performance does not guarantee future results
- Risk warnings for speculative investments`

export function createInvestmentAgent(model: string = DEFAULT_MODEL): AgentConfig {
  return {
    description: "Investment Agent - Portfolio analysis and investment research with Exa web search",
    mode: "subagent",
    model,
    prompt: INVESTMENT_AGENT_PROMPT,
    color: "#FFD700",
    tools: {
      execute_sql: true,
      web_search_exa: true,
    },
  }
}

export const investmentAgent = createInvestmentAgent()
```

### 3.5 Tax Specialist BR

**`src/agents/finances/tax-specialist-br.ts`**

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"

const DEFAULT_MODEL = "google/gemini-3-pro-preview"

const TAX_SPECIALIST_BR_PROMPT = `<Role>
You are "Tax Specialist BR" - Expert in Brazilian tax law and IRPF (Imposto de Renda Pessoa Física).

**Expertise**:
- Brazilian federal taxes (IRPF, IOF, CSLL)
- Deduction optimization
- Tax planning strategies
- Deadline reminders
- Simple-to-complex income reporting
- Stock market taxation (day trade, swing trade, FIIs)

**Knowledge Base**:
- Receita Federal regulations
- CVM tax rules
- Tax treaties
- State and municipal taxes (ISS, IPVA)

## Tax Year Cycle

### January-March: Preparation
- Gather income documents ( Informe de Rendimentos )
- Organize investment statements
- Track medical/education expenses

### April: Declaration
- IRPF declaration window (usually April 1-30)
- Help users file correctly
- Identify common mistakes

### May-December: Planning
- Optimize withholdings
- Plan for next year
- Track capital gains

## Common Queries

| Query | Response |
|-------|----------|
| "How do I declare stock gains?" | Explain taxing rules (15% or 20% depending on volume) |
| "Can I deduct this?" | List deductible expenses per Receita Federal |
| "What's my tax rate?" | Progressive brackets for IRPF |

## Supabase Queries

\`\`\`typescript
// Capital gains summary
execute_sql({
  query: \`
    SELECT
      DATE_TRUNC('month', date) as month,
      SUM(CASE WHEN type = 'gain' THEN amount ELSE 0 END) as gains,
      SUM(CASE WHEN type = 'loss' THEN ABS(amount) ELSE 0 END) as losses
    FROM transactions
    WHERE user_id = ? AND category = 'stocks'
    GROUP BY month
    ORDER BY month
  \`,
  params: [user_id]
})
\`\`\`

## Output Guidelines

1. **Clarity** - Explain in simple terms
2. **Accuracy** - Cite current regulations
3. **Disclaimer** - "Not a tax advisor. Consult a professional."
4. **Actionability** - Clear next steps

## Key Brazilian Tax Rules (2024)

- **IRPF**: Progressive rates 0% to 27.5% (exemptions up to R$ 24.751)
- **Stock Gains**: 15% (up to R$ 20M/month), 20% above
- **FIIs**: Tax-free dividends (0% withholding)
- **Day Trade**: 20% on gains, minimum R$ 1
- **Cryptocurrency**: 15% on gains (above R$ 35K)`

export function createTaxSpecialistBRAgent(model: string = DEFAULT_MODEL): AgentConfig {
  return {
    description: "Tax Specialist BR - Brazilian tax expert for IRPF, deductions, and compliance",
    mode: "subagent",
    model,
    prompt: TAX_SPECIALIST_BR_PROMPT,
    color: "#DC143C",
    tools: {
      execute_sql: true,
      web_search_exa: true,  // For web search on tax regulations
    },
  }
}

export const taxSpecialistBRAgent = createTaxSpecialistBRAgent()
```

### 3.6 Regulatory Agent

**`src/agents/finances/regulatory-agent.ts`**

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"

const DEFAULT_MODEL = "google/gemini-3-pro-preview"

const REGULATORY_AGENT_PROMPT = `<Role>
You are "Regulatory Agent" - Expert in Brazilian financial regulations and compliance.

**Expertise**:
- CVM (Comissão de Valores Mobiliários) rules
- Central Bank (BCB) regulations
- ANBIMA guidelines
- Tax authority (Receita Federal) updates
- Compliance requirements for investors

**Mission**: Keep users informed about regulatory changes that affect their investments and financial decisions.
</Role>

## Workflow

### 1. Monitor Regulations
- Use Exa MCP to search for recent regulatory updates
- Track CVM, BCB, Receita Federal announcements
- Identify changes affecting personal finance

### 2. Analyze Impact
- Assess how changes affect user portfolio
- Identify compliance requirements
- Flag deadlines and action items

### 3. Communicate Clearly
- Summarize regulations in plain language
- Highlight actionable items
- Provide context for financial decisions

## Exa Search Patterns

\`\`\`typescript
// Recent CVM regulations
web_search_exa({
  query: "CVM regulação investimento 2024",
  numResults: 10
})

// Central Bank updates
web_search_exa({
  query: "Banco Central BCB política monetária 2024",
  numResults: 5
})

// Tax authority announcements
web_search_exa({
  query: "Receita Federal imposto renda mudança 2024",
  numResults: 10
})
\`\`\`

## Output Structure

1. **Update Summary** - What changed
2. **Impact Analysis** - How it affects users
3. **Action Items** - What users should do
4. **Deadlines** - Important dates
5. **Sources** - Official documents and links

## Key Regulatory Bodies

| Body | Scope | Search Terms |
|------|-------|--------------|
| CVM | Securities market | "CVM regulação", "instrução CVM" |
| BCB | Monetary policy | "Banco Central", "taxa Selic", "PIX" |
| Receita Federal | Tax | "Receita Federal", "IRPF", "malha fina" |
| ANBIMA | Asset management | "ANBIMA", "fundos de investimento" |

## Critical: Stay Current

Always verify information is from official sources and reflects current (not outdated) regulations.`

export function createRegulatoryAgent(model: string = DEFAULT_MODEL): AgentConfig {
  return {
    description: "Regulatory Agent - Brazilian financial regulations, CVM rules, and compliance updates",
    mode: "subagent",
    model,
    prompt: REGULATORY_AGENT_PROMPT,
    color: "#2E8B57",
    tools: {
      web_search_exa: true,  // For web search on CVM, BCB, regulations
    },
  }
}

export const regulatoryAgent = createRegulatoryAgent()
```

---

## 4. Type System Integration

### Update `src/agents/types.ts`

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"
import { isGptModel } from "./types"

/**
 * Agent category for grouping in Finances prompt sections
 */
export type FinancesAgentCategory =
  | "orchestration"  // Main orchestrator
  | "data"           // Wallet, Budget
  | "analysis"       // Investment
  | "knowledge"      // Tax, Regulatory
  | "support"        // Document Writer

/**
 * Cost classification for Tool Selection table
 */
export type FinancesAgentCost = "FREE" | "CHEAP" | "EXPENSIVE"

/**
 * Delegation trigger for Finances prompt's Delegation Table
 */
export interface FinancesDelegationTrigger {
  domain: string
  trigger: string
}

/**
 * Metadata for generating Finances prompt sections dynamically
 */
export interface FinancesAgentPromptMetadata {
  category: FinancesAgentCategory
  cost: FinancesAgentCost
  triggers: FinancesDelegationTrigger[]
  useWhen?: string[]
  avoidWhen?: string[]
  dedicatedSection?: string
  promptAlias?: string
  keyTrigger?: string
}

// Extend BuiltinAgentName type
export type BuiltinAgentName =
  | "Sisyphus"
  | "oracle"
  | "librarian"
  | "explore"
  | "frontend-ui-ux-engineer"
  | "document-writer"
  | "multimodal-looker"
  | "Metis (Plan Consultant)"
  | "Momus (Plan Reviewer)"
  | "orchestrator-sisyphus"
  | "finances-orchestrator"      // Main orchestrator
  | "wallet-agent"               // Personal finance
  | "budget-analyst"             // Budgeting
  | "investment-agent"           // Investments
  | "tax-specialist-br"          // Brazilian taxes
  | "regulatory-agent"           // Compliance

// Helper for Gemini model detection
export function isGeminiModel(model: string): boolean {
  return model.includes("gemini")
}
```

---

## 5. Agent Registration

### Update `src/agents/index.ts`

```typescript
import type { AgentConfig } from "@opencode-ai/sdk"
import { sisyphusAgent } from "./sisyphus"
import { oracleAgent } from "./oracle"
import { librarianAgent } from "./librarian"
import { exploreAgent } from "./explore"
import { frontendUiUxEngineerAgent } from "./frontend-ui-ux-engineer"
import { documentWriterAgent } from "./document-writer"
import { multimodalLookerAgent } from "./multimodal-looker"
import { metisAgent } from "./metis"
import { orchestratorSisyphusAgent } from "./orchestrator-sisyphus"
import { momusAgent } from "./momus"

// Finances agents
import { financesOrchestratorAgent } from "./finances/orchestrator"
import { walletAgent } from "./finances/wallet-agent"
import { budgetAnalystAgent } from "./finances/budget-analyst"
import { investmentAgent } from "./finances/investment-agent"
import { taxSpecialistBRAgent } from "./finances/tax-specialist-br"
import { regulatoryAgent } from "./finances/regulatory-agent"

export const builtinAgents: Record<string, AgentConfig> = {
  Sisyphus: sisyphusAgent,
  oracle: oracleAgent,
  librarian: librarianAgent,
  explore: exploreAgent,
  "frontend-ui-ux-engineer": frontendUiUxEngineerAgent,
  "document-writer": documentWriterAgent,
  "multimodal-looker": multimodalLookerAgent,
  "Metis (Plan Consultant)": metisAgent,
  "Momus (Plan Reviewer)": momusAgent,
  "orchestrator-sisyphus": orchestratorSisyphusAgent,

  // Finances agents
  "finances-orchestrator": financesOrchestratorAgent,
  "wallet-agent": walletAgent,
  "budget-analyst": budgetAnalystAgent,
  "investment-agent": investmentAgent,
  "tax-specialist-br": taxSpecialistBRAgent,
  "regulatory-agent": regulatoryAgent,
}

export * from "./types"
export { createBuiltinAgents } from "./utils"
export type { AvailableAgent } from "./sisyphus-prompt-builder"
```

### Update `src/agents/utils.ts`

```typescript
// Add to agentSources
const agentSources: Record<BuiltinAgentName, AgentSource> = {
  // ... existing agents
  "finances-orchestrator": createFinancesOrchestratorAgent,
  "wallet-agent": createWalletAgent,
  "budget-analyst": createBudgetAnalystAgent,
  "investment-agent": createInvestmentAgent,
  "tax-specialist-br": createTaxSpecialistBRAgent,
  "regulatory-agent": createRegulatoryAgent,
}

// Add to agentMetadata
const agentMetadata: Partial<Record<BuiltinAgentName, AgentPromptMetadata>> = {
  // ... existing
  "finances-orchestrator": {
    category: "orchestration",
    cost: "EXPENSIVE",
    triggers: [
      { domain: "General Finance", trigger: "Any financial question" },
      { domain: "Multi-agent Task", trigger: "Complex analysis requiring multiple specialists" },
    ],
    keyTrigger: "finances, financial, money, budget, investment, tax",
  },
  "wallet-agent": {
    category: "data",
    cost: "CHEAP",
    triggers: [
      { domain: "Transactions", trigger: "balance, transaction, expense, income" },
      { domain: "Account", trigger: "account, wallet, spending" },
    ],
    keyTrigger: "balance, transactions, expenses, spending",
  },
  "budget-analyst": {
    category: "data",
    cost: "CHEAP",
    triggers: [
      { domain: "Budget", trigger: "budget, forecast, variance, KPI" },
    ],
    keyTrigger: "budget, forecast, variance",
  },
  "investment-agent": {
    category: "analysis",
    cost: "EXPENSIVE",
    triggers: [
      { domain: "Portfolio", trigger: "portfolio, investments, holdings" },
      { domain: "Opportunities", trigger: "opportunity, research, stock, FII" },
    ],
    keyTrigger: "invest, portfolio, stock, opportunity",
  },
  "tax-specialist-br": {
    category: "knowledge",
    cost: "EXPENSIVE",
    triggers: [
      { domain: "Taxes", trigger: "tax, imposto, IRPF, deduction" },
    ],
    keyTrigger: "tax, imposto, IRPF, deduction, declare",
  },
  "regulatory-agent": {
    category: "knowledge",
    cost: "EXPENSIVE",
    triggers: [
      { domain: "Regulations", trigger: "regulation, CVM, compliance, BCB" },
    ],
    keyTrigger: "regulation, CVM, compliance, rule",
  },
}

// Update createBuiltinAgents to handle finances orchestrator specially
```

---

## 6. Supabase Schema

### 7.1 Database Schema

```sql
-- =====================================================
-- FINANCES AGENT TEAM - SUPABASE SCHEMA
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_chat_id BIGINT UNIQUE,
    email TEXT,
    name TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- SESSIONS TABLE (Lightweight session tracking)
-- =====================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    opencode_session_id TEXT UNIQUE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    summary TEXT,
    model_used TEXT,
    cost_estimate DECIMAL(10, 4),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- TRANSACTIONS TABLE
-- =====================================================
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer', 'investment')),
    category TEXT NOT NULL,
    subcategory TEXT,
    description TEXT,
    date DATE NOT NULL,
    receipt_url TEXT,
    audio_transcription TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_transactions_user_date ON transactions(user_id, date);
CREATE INDEX idx_transactions_category ON transactions(user_id, category);
CREATE INDEX idx_transactions_type ON transactions(user_id, type);

-- =====================================================
-- PORTFOLIOS TABLE
-- =====================================================
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    holdings JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_value DECIMAL(14, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- BUDGETS TABLE
-- =====================================================
CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    budgeted_amount DECIMAL(12, 2) NOT NULL,
    period_type TEXT DEFAULT 'monthly' CHECK (period_type IN ('weekly', 'monthly', 'quarterly', 'yearly')),
    start_date DATE NOT NULL,
    end_date DATE,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- ANALYSES TABLE (Agent outputs)
-- =====================================================
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('budget', 'investment', 'tax', 'regulatory', 'portfolio', 'general')),
    findings JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    visualizations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- DOCUMENTS TABLE (Generated reports)
-- =====================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT 'markdown' CHECK (type IN ('markdown', 'pdf', 'html')),
    file_path TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- COMPLIANCE_UPDATES TABLE (Regulatory tracking)
-- =====================================================
CREATE TABLE compliance_updates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    effective_date DATE,
    impact_level TEXT CHECK (impact_level IN ('low', 'medium', 'high')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- FUNCTION: Update timestamp on row update
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER update_users_timestamp BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_transactions_timestamp BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_portfolios_timestamp BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_budgets_timestamp BEFORE UPDATE ON budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =====================================================
-- SAMPLE DATA (For testing)
-- =====================================================
INSERT INTO users (telegram_chat_id, name, preferences) VALUES
(123456789, 'User', '{"language": "pt-BR", "currency": "BRL"}');

-- Sample budget
INSERT INTO budgets (user_id, name, category, budgeted_amount, period_type, start_date, active)
SELECT id, 'Monthly Food Budget', 'Food', 2000, 'monthly', DATE_TRUNC('month', NOW()), true
FROM users WHERE telegram_chat_id = 123456789 LIMIT 1;
```

### 7.2 Row Level Security (RLS)

```sql
-- Enable RLS on all user tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Create policies to ensure users can only see their own data
CREATE POLICY "Users can view own data" ON users FOR SELECT
    USING (auth.uid()::TEXT = (SELECT id::TEXT FROM users WHERE telegram_chat_id = current_setting('app.user_chat_id', true)::BIGINT));

CREATE POLICY "Users can manage own transactions" ON transactions FOR ALL
    USING (user_id IN (SELECT id FROM users WHERE telegram_chat_id = current_setting('app.user_chat_id', true)::BIGINT));

-- Similar policies for other tables...
```

---

## 8. Telegram Integration

### 8.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TELEGRAM REPO (Python)                              │
│                                                                          │
│   ┌──────────────┐                                                      │
│   │ Telegram Bot │◀─── User Messages                                    │
│   │ (python-telegram-bot)                                               │
│   └──────┬───────┘                                                      │
│          │                                                              │
│          ▼                                                              │
│   ┌──────────────┐                                                      │
│   │ Session      │                                                      │
│   │ Manager      │───▶ Tailscale SSH Tunnel (100.x.x.x:5147)           │
│   │              │◀─── Webhook Response                                 │
│   └──────┬───────┘                                                      │
│          │                                                              │
│          ▼                                                              │
│   ┌──────────────┐                                                      │
│   │ Logs & Docs  │                                                      │
│   │ - sessions/  │                                                      │
│   │ - docs/      │                                                      │
│   └──────────────┘                                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Tailscale IP + SSH
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              OH-MY-OPENCODE (Your MacBook)                              │
│                                                                          │
│   Finances Orchestrator Agent                                            │
│   ├── Wallet Agent                                                      │
│   ├── Budget Analyst                                                    │
│   ├── Investment Agent + Exa MCP                                         │
│   ├── Tax Specialist BR                                                 │
│   └── Regulatory Agent                                                  │
│                                                                          │
│   MCP SERVERS:                                                          │
│   ├── Supabase MCP → PostgreSQL                                         │
│   ├── Exa MCP → Semantic Web Search                                     │
│   ├── Gemini 1.5 Pro → Multimodal                                       │
│   └── Gemini Flash → Quick Queries                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 SSH Tunnel via Tailscale

Tailscale provides a secure, private network with stable IPs for your devices. Connect your Telegram repo to OpenCode using the Tailscale IP.

```python
# telegram-repo/src/ssh_tunnel.py

import asyncio
import asyncssh

# Get your Tailscale IP from: tailscale ip
TAILSCALE_IP = "100.x.x.x"  # Your MacBook's Tailscale IP
OPENCODE_PORT = 5147

async def create_tailscale_tunnel(
    remote_host: str = TAILSCALE_IP,
    remote_port: int = OPENCODE_PORT,
    local_port: int = OPENCODE_PORT,
    ssh_user: str = "your_username",
    ssh_key: str = "~/.ssh/id_ed25519"  # SSH key path
):
    """
    Create SSH tunnel to OpenCode server via Tailscale network.

    Prerequisites:
    1. Install Tailscale on both devices
    2. Authenticate both devices to your Tailscale network
    3. Get your MacBook's Tailscale IP: `tailscale ip`
    4. Enable SSH on your MacBook: System Settings → Sharing → Remote Login

    Usage:
        python ssh_tunnel.py

    The tunnel connects:
    - Local (Telegram repo): localhost:5147
    - Remote (OpenCode): 100.x.x.x:5147 (your Tailscale IP)
    """

    print(f"🔗 Connecting to OpenCode via Tailscale...")
    print(f"   Target: {remote_host}:{remote_port}")

    try:
        async with asyncssh.connect(
            host=remote_host,
            port=22,  # SSH port on MacBook
            username=ssh_user,
            client_keys=[ssh_key],  # SSH key authentication
            known_hosts=None,  # Disable host verification for local network
        ) as conn:
            # Create reverse tunnel: remote:5147 -> local:5147
            await conn.create_reverse_tunnel(
                remote_host, remote_port,
                local_host, local_port
            )

            print(f"✅ SSH tunnel established!")
            print(f"   Local:  localhost:{local_port}")
            print(f"   Remote: {remote_host}:{remote_port}")
            print(f"   Tailscale IP: {remote_host}")

            # Keep tunnel running
            await asyncio.Future()

    except Exception as e:
        print(f"❌ Failed to establish tunnel: {e}")
        print(f"   Make sure:")
        print(f"   1. Tailscale is running on both devices")
        print(f"   2. SSH is enabled on your MacBook")
        print(f"   3. SSH key is correctly configured")
        raise

if __name__ == "__main__":
    asyncio.run(create_tailscale_tunnel())
```

### 8.3 Telegram Bot Handler

```python
# telegram-repo/src/bot.py

import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from session_manager import SessionManager
from ssh_tunnel import check_tunnel

# Initialize session manager
session_manager = SessionManager()

async def start_tunnel():
    """Ensure SSH tunnel is active"""
    if not await check_tunnel():
        print("⚠️ SSH tunnel not active. Starting...")
        # Start tunnel in background
        asyncio.create_task(create_ssh_tunnel())

async def handle_message(update: Update, context):
    """Handle incoming messages from Telegram"""

    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message.text

    # Log incoming message
    print(f"📨 From {user.name} ({chat_id}): {message}")

    # Check if session exists or create new
    session = session_manager.get_or_create(chat_id)

    if session.is_active:
        # Continue existing session
        response = await session.continue_session(message)
    else:
        # Start new session
        response = await session.start_new(message)

    # Send response
    await update.message.reply_text(
        response,
        parse_mode='Markdown'
    )

async def handle_voice(update: Update, context):
    """Handle voice messages - forward to Gemini 1.5 Pro"""

    voice = update.message.voice
    file = await voice.get_file()

    # Download audio
    audio_path = f"/tmp/{voice.file_id}.ogg"
    await file.download_to_drive(audio_path)

    # Send to OpenCode for transcription + analysis
    session = session_manager.get_or_create(update.effective_chat.id)
    response = await session.send_audio(audio_path)

    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_photo(update: Update, context):
    """Handle photos - receipt analysis, etc."""

    photo = update.message.photo[-1]  # Highest resolution
    file = await photo.get_file()

    image_path = f"/tmp/{photo.file_id}.jpg"
    await file.download_to_drive(image_path)

    session = session_manager.get_or_create(update.effective_chat.id)
    response = await session.send_image(image_path)

    await update.message.reply_text(response, parse_mode='Markdown')

async def main():
    # Ensure tunnel is active
    await start_tunnel()

    # Create application
    app = Application.builder().token("YOUR_BOT_TOKEN").build()

    # Add handlers
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Olá! Sou seu assistente de finanças. Como posso ajudar?")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Start polling
    print("🤖 Telegram bot started")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
```

### 8.4 Session Manager

```python
# telegram-repo/src/session_manager.py

import httpx
import json
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Session:
    chat_id: int
    opencode_session_id: Optional[str] = None
    is_active: bool = False
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] None

class SessionManager:
    def __init__(self, opencode_url: str = "http://localhost:5147"):
        self.opencode_url = opencode_url
        self.sessions: dict[int, Session] = {}
        self.http_client = httpx.AsyncClient(timeout=300.0)

    def get_or_create(self, chat_id: int) -> Session:
        """Get existing session or create new one"""
        if chat_id not in self.sessions:
            self.sessions[chat_id] = Session(chat_id=chat_id)
        return self.sessions[chat_id]

    async def start_new(self, message: str) -> str:
        """Start new OpenCode session"""
        session = self.get_or_create(self.chat_id)

        # Call OpenCode API to start session
        response = await self.http_client.post(
            f"{self.opencode_url}/session/start",
            json={
                "message": message,
                "chat_id": self.chat_id,
                "model": "google/gemini-3-pro-preview"
            }
        )

        if response.status_code == 200:
            data = response.json()
            session.opencode_session_id = data["session_id"]
            session.is_active = True
            session.started_at = datetime.now()

            # Return summary (webhook will send full response)
            return f"🔄 Processando sua solicitação...\n\n📊 Session ID: `{data['session_id']}`\n\n⏳ Aguarde a análise ser concluída."
        else:
            return "❌ Erro ao iniciar sessão. Tente novamente."

    async def continue_session(self, message: str) -> str:
        """Continue existing session"""
        session = self.get_or_create(self.chat_id)

        response = await self.http_client.post(
            f"{self.opencode_url}/session/{session.opencode_session_id}/continue",
            json={"message": message}
        )

        return response.json()["response"]

    async def send_audio(self, audio_path: str) -> str:
        """Send audio for transcription + analysis"""
        session = self.get_or_create(self.chat_id)

        with open(audio_path, "rb") as f:
            files = {"audio": f}
            data = {"chat_id": self.chat_id}
            response = await self.http_client.post(
                f"{self.opencode_url}/session/{session.opencode_session_id}/audio",
                files=files,
                data=data
            )

        return response.json()["response"]

    async def send_image(self, image_path: str) -> str:
        """Send image for analysis"""
        session = self.get_or_create(self.chat_id)

        with open(image_path, "rb") as f:
            files = {"image": f}
            data = {"chat_id": self.chat_id}
            response = await self.http_client.post(
                f"{self.opencode_url}/session/{session.opencode_session_id}/image",
                files=files,
                data=data
            )

        return response.json()["response"]

    async def get_status(self, chat_id: int) -> dict:
        """Get session status"""
        session = self.sessions.get(chat_id)
        if not session:
            return {"status": "no_active_session"}

        return {
            "status": "active" if session.is_active else "completed",
            "session_id": session.opencode_session_id,
            "started_at": session.started_at.isoformat() if session.started_at else None
        }
```

---

## 9. Session Management

### 9.1 Session Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       SESSION LIFECYCLE                                 │
│                                                                         │
│  1. TRIGGER (Telegram)                                                 │
│     User sends message → SessionManager checks for active session      │
│                              │                                          │
│                              ▼                                          │
│  2. START (OpenCode)                                                   │
│     POST /session/start → Creates OpenCode session                     │
│     Returns session_id → Telegram sends "Processing..."                │
│                              │                                          │
│                              ▼                                          │
│  3. EXECUTION                                                          │
│     Finances Orchestrator receives message                              │
│     → Intent classification                                             │
│     → Delegates to subagents                                           │
│     → Synthesizes response                                             │
│                              │                                          │
│                              ▼                                          │
│  4. COMPLETION                                                         │
│     Webhook to Telegram with summary                                   │
│     → Session marked complete in Supabase                              │
│     → Document saved (if generated)                                    │
│                              │                                          │
│                              ▼                                          │
│  5. CONTINUE (Optional)                                                │
│     User says "continue"                                               │
│     → Resume same session_id                                           │
│     → Full context preserved                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Session Persistence Strategy

The key insight is: **Don't store full conversation history in Supabase. Store pointers.**

```typescript
// What to store in Supabase sessions table
interface SessionSummary {
  session_id: string;           // OpenCode session ID
  user_id: UUID;                // From telegram_chat_id
  started_at: DateTime;
  completed_at?: DateTime;
  summary: string;              // 1-2 sentence summary
  model_used: string;           // e.g., "gemini-3-pro-preview"
  cost_estimate: number;        // Token cost estimate
  data_pointers: {              // Pointers to fresh data
    transactions_last_query: string;
    portfolios_last_query: string;
  };
  agent_results: [              // Summary of agent outputs
    { agent: string; type: string; finding_summary: string }
  ];
  metadata: JSONB;              // Additional context
}

// What NOT to store
// ❌ Full conversation history (too expensive, stale)
// ❌ All intermediate agent outputs (redundant)
// ❌ Raw query results (can re-query from Supabase)

// What OpenCode keeps in context
// ✅ Current conversation (managed by OpenCode)
// ✅ Recent data (in context window)
// ✅ Compiled insights (from agents)
```

### 9.3 Continue Workflow

```typescript
// When user says "continue"
async function handleContinue(sessionId: string, message: string) {
  // 1. Load session summary from Supabase
  const session = await execute_sql({
    query: "SELECT * FROM sessions WHERE opencode_session_id = ?",
    params: [sessionId]
  });

  // 2. Get fresh data pointers
  const pointers = session.data_pointers;

  // 3. Create continuation prompt
  const prompt = `
    ## Previous Session Context
    ${session.summary}

    ## Data Pointers (re-query these for fresh data)
    - Transactions: ${pointers.transactions_last_query}
    - Portfolios: ${pointers.portfolios_last_query}

    ## User Request
    ${message}

    ## Task
    Continue the analysis using fresh data from Supabase.
  `;

  // 4. Start new OpenCode session with context
  const newSession = await opencode.startSession({
    systemPrompt: session.system_context,  // Lightweight context
    userPrompt: prompt
  });

  // 5. Return response
  return newSession.response;
}
```

---

## 10. Implementation Checklist

### Phase 1: Core Agent Team

- [ ] Create `src/agents/finances/orchestrator.ts`
- [ ] Create `src/agents/finances/wallet-agent.ts`
- [ ] Create `src/agents/finances/budget-analyst.ts`
- [ ] Create `src/agents/finances/investment-agent.ts`
- [ ] Create `src/agents/finances/tax-specialist-br.ts`
- [ ] Create `src/agents/finances/regulatory-agent.ts`
- [ ] Update `src/agents/index.ts` with all agents
- [ ] Update `src/agents/types.ts` with new types
- [ ] Update `src/agents/utils.ts` with agent sources and metadata

### Phase 2: MCP Integration

- [ ] Create `src/tools/supabase-mcp/tools.ts`
- [ ] Configure Supabase connection in MCP
- [ ] Create Exa MCP integration pattern
- [ ] Create Gemini 1.5 Pro multimodal tool wrapper

### Phase 3: Supabase Setup

- [ ] Run database schema SQL
- [ ] Configure RLS policies
- [ ] Create test data for development
- [ ] Test Supabase connection from agents

### Phase 4: Skills (Optional)

- [ ] Create `src/features/builtin-skills/finances/investment-skill/SKILL.md`
- [ ] Create `src/features/builtin-skills/finances/tax-br-skill/SKILL.md`
- [ ] Create `src/features/builtin-skills/finances/wallet-skill/SKILL.md`

### Phase 5: Hooks (Optional)

- [ ] Create `src/hooks/finances-orchestrator/index.ts`
- [ ] Implement session tracking
- [ ] Add webhook handlers

### Phase 6: Testing

- [ ] Write unit tests for each agent
- [ ] Test MCP tool integration
- [ ] Test Supabase queries
- [ ] Test session management
- [ ] Integration test with Telegram (simulated)

---

## 11. Testing Guidelines

### 11.1 Unit Tests

```typescript
// src/agents/finances/wallet-agent.test.ts

import { describe, it, expect } from "bun:test"
import { createWalletAgent } from "./wallet-agent"

describe("Wallet Agent", () => {
  it("creates agent with default model", () => {
    const agent = createWalletAgent()
    expect(agent.model).toBe("google/gemini-3-pro-preview")
    expect(agent.mode).toBe("subagent")
    expect(agent.color).toBe("#4169E1")
  })

  it("includes Supabase tools", () => {
    const agent = createWalletAgent()
    expect((agent.tools as Record<string, unknown>).execute_sql).toBe(true)
    expect((agent.tools as Record<string, unknown>).execute_sql).toBe(true)
  })

  it("includes prompt sections", () => {
    const agent = createWalletAgent()
    expect(agent.prompt).toContain("Role")
    expect(agent.prompt).toContain("Core Functions")
    expect(agent.prompt).toContain("Query Patterns")
  })
})
```

### 11.2 Integration Tests

```typescript
// src/tools/supabase-mcp/tools.test.ts

import { describe, it, expect, beforeAll } from "bun:test"
import { SupabaseClient } from "./tools"

describe("Supabase MCP", () => {
  let client: SupabaseClient

  beforeAll(() => {
    client = new SupabaseClient({
      connectionString: process.env.SUPABASE_URL,
      apiKey: process.env.SUPABASE_API_KEY
    })
  })

  it("connects and queries transactions", async () => {
    const result = await client.query({
      query: "SELECT COUNT(*) as count FROM transactions LIMIT 1",
      params: []
    })
    expect(result).toHaveProperty("data")
    expect(result.data).toHaveProperty("count")
  })

  it("inserts and deletes a test record", async () => {
    // Insert
    const insert = await client.insert({
      table: "transactions",
      data: {
        amount: 100.00,
        type: "expense",
        category: "test",
        description: "Integration test",
        date: new Date().toISOString().split("T")[0]
      }
    })
    expect(insert.data).toHaveProperty("id")

    // Clean up
    await client.delete({
      table: "transactions",
      id: insert.data.id
    })
  })
})
```

---

## 12. Quick Reference

### Agent Quick Reference

| Agent | Trigger Keywords | Model | Color |
|-------|-----------------|-------|-------|
| **Finances Orchestrator** | finance, budget, investment | Gemini 3 Pro | #228B22 |
| **Wallet Agent** | balance, transaction, expense | Gemini 3 Pro | #4169E1 |
| **Budget Analyst** | budget, forecast, variance | Gemini 3 Pro | #9932CC |
| **Investment Agent** | invest, portfolio, stock | Gemini 3 Pro + Exa | #FFD700 |
| **Tax Specialist BR** | tax, imposto, IRPF | Gemini 3 Pro + Exa | #DC143C |
| **Regulatory Agent** | regulation, CVM, compliance | Gemini 3 Pro + Exa | #2E8B57 |

### Supabase Quick Query Reference

| Query | SQL |
|-------|-----|
| Balance | `SELECT SUM(CASE WHEN type='income' THEN amount ELSE -amount END) FROM transactions WHERE user_id = ?` |
| By Category | `SELECT category, SUM(amount) FROM transactions WHERE user_id = ? AND type='expense' GROUP BY category` |
| Recent | `SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC LIMIT 50` |
| Budget vs Actual | `SELECT b.category, b.budgeted_amount, COALESCE(SUM(t.amount),0) as actual FROM budgets b LEFT JOIN transactions t ON...` |

### Exa Search Reference

| Task | Exa Command |
|------|-------------|
| Market research | `web_search_exa({ query: "..." })` |
| Investment news | `web_search_exa({ query: "..." })` |
| Regulatory updates | `web_search_exa({ query: "..." })` |

---

## Summary

This documentation provides a complete guide for implementing a **Finances Agent Team** in oh-my-opencode. The architecture follows the established Sisyphus patterns while extending them for financial domain expertise.

### Key Takeaways

1. **Finances Orchestrator** is the main agent (like Sisyphus)
2. **Subagents** handle specific domains (Wallet, Budget, Investment, Tax, Regulatory)
3. **Gemini models** are used throughout (Flash for quick, Pro for complex, 1.5 Pro for multimodal)
4. **Supabase MCP** provides direct PostgreSQL access for data persistence
5. **Exa MCP** enables semantic web search for market research
6. **Telegram integration** uses Tailscale SSH tunnel for secure connection
7. **Session management** stores lightweight summaries, not full history

### Next Steps

1. Implement agents in order (orchestrator first, then subagents)
2. Set up Supabase database with provided schema
3. Create MCP tools for Supabase integration
4. Test each agent individually
5. Integration test with Telegram (simulated)
6. Deploy to local environment

---

## References

- **Sisyphus Implementation**: `src/agents/sisyphus.ts`
- **Agent Types**: `src/agents/types.ts`
- **Agent Factory**: `src/agents/utils.ts`
- **Tool Integration**: `src/tools/delegate-task/tools.ts`
- **Hook System**: `src/hooks/sisyphus-orchestrator/index.ts`
- **Main Plugin**: `src/index.ts`
- **Config Schema**: `src/config/schema.ts`
