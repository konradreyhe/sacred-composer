# Engineering Principles

**Purpose:** Core engineering principles that guide all development in this codebase.

**Audience:** All developers, AI assistants, code reviewers

**Status:** Living document - updated as we learn

---

## 🧭 Core Philosophy

> **"Optimize for clarity and adaptability, not perfection."**

This codebase prioritizes:
- ✅ **Maintainable** - Easy to understand and change
- ✅ **Evolvable** - Adaptable to new requirements
- ✅ **Documented** - Clear context for future developers
- ❌ **NOT Perfect** - Good enough is better than perfect

---

## 🎯 Guiding Principles

### 1. KISS – Keep It Simple, Stupid

**Rule:** The simplest solution that works is the best solution.

**In Practice:**
- Favor clarity over cleverness
- Break complex logic into small, understandable pieces
- Avoid over-engineering and premature optimization
- No "clever" code that sacrifices readability

**Example:**
```typescript
// ❌ BAD: Clever but hard to understand
const result = data.reduce((acc, x) => ({ ...acc, [x.id]: x }), {});

// ✅ GOOD: Clear and explicit
const result: Record<string, Item> = {};
for (const item of data) {
  result[item.id] = item;
}
```

**Anti-Perfection Rule:** Prefer clear, working solutions over complex "perfect" ones.

---

### 2. DRY – Don't Repeat Yourself

**Rule:** Every piece of knowledge should have a single, unambiguous representation.

**In Practice:**
- Extract common logic into reusable functions/modules
- Externalize configuration (don't hardcode)
- Define constants for magic numbers
- Share types/interfaces across modules

**Example:**
```typescript
// ❌ BAD: Repeated validation logic
function createUser(email: string) {
  if (!email.includes('@')) throw new Error('Invalid email');
  // ...
}
function updateUser(email: string) {
  if (!email.includes('@')) throw new Error('Invalid email');
  // ...
}

// ✅ GOOD: Reusable validation
function validateEmail(email: string): void {
  if (!email.includes('@')) throw new Error('Invalid email');
}

function createUser(email: string) {
  validateEmail(email);
  // ...
}
```

**Note:** DRY applies to *knowledge* and *business logic*, not necessarily code. Sometimes duplication is better than the wrong abstraction.

---

### 3. YAGNI – You Ain't Gonna Need It

**Rule:** Only implement features you actually need right now.

**In Practice:**
- Don't add functionality "just in case"
- No speculative features or abstractions
- Remove unused code and commented-out blocks
- Avoid over-abstraction

**Example:**
```typescript
// ❌ BAD: Building for future features we don't need yet
class UserService {
  async createUser() { /* ... */ }
  async updateUser() { /* ... */ }
  async deleteUser() { /* ... */ }
  async restoreUser() { /* ... */ }  // Not needed yet!
  async archiveUser() { /* ... */ }  // Not needed yet!
  async exportUser() { /* ... */ }   // Not needed yet!
}

// ✅ GOOD: Only what we need now
class UserService {
  async createUser() { /* ... */ }
  async updateUser() { /* ... */ }
  async deleteUser() { /* ... */ }
}
// Add other methods when actually needed
```

---

### 4. SRP – Single Responsibility Principle

**Rule:** Each function/class should have one, and only one, reason to change.

**In Practice:**
- Functions should do one thing and do it well
- Classes should have a single, clear responsibility
- No "god objects" or monolithic functions
- Clear separation of concerns

**Example:**
```typescript
// ❌ BAD: Function does too many things
async function handleUserRegistration(email: string, password: string) {
  validateEmail(email);
  validatePassword(password);
  const hashedPassword = await bcrypt.hash(password, 10);
  const user = await db.users.create({ email, password: hashedPassword });
  await emailService.sendWelcomeEmail(email);
  await analyticsService.trackRegistration(user.id);
  await auditLog.log('USER_REGISTERED', user.id);
  return user;
}

// ✅ GOOD: Each function has single responsibility
async function createUser(email: string, password: string): Promise<User> {
  const hashedPassword = await hashPassword(password);
  return db.users.create({ email, password: hashedPassword });
}

async function handleUserRegistration(email: string, password: string): Promise<User> {
  validateUserInput(email, password);
  const user = await createUser(email, password);
  await sendWelcomeEmail(user.email);
  await trackRegistration(user.id);
  await logUserCreated(user.id);
  return user;
}
```

---

### 5. High Cohesion / Low Coupling

**Rule:** Related functionality should be grouped together; modules should minimize dependencies.

**In Practice:**
- Group related functions/classes in the same module
- Minimize dependencies between modules
- Use clear interfaces/contracts
- Make modules easy to test in isolation

**Example:**
```
// ✅ GOOD: High cohesion - related things together
src/users/
├── users.service.ts       # User business logic
├── users.controller.ts    # HTTP handlers
├── users.repository.ts    # Database access
├── dto/
│   ├── create-user.dto.ts
│   └── update-user.dto.ts
└── entities/
    └── user.entity.ts

// ✅ GOOD: Low coupling - clear boundaries
UsersService depends on UsersRepository (interface)
UsersController depends on UsersService
No circular dependencies
```

---

### 6. Composition > Inheritance

**Rule:** Favor composition over inheritance for code reuse.

**In Practice:**
- Use interfaces/types for contracts
- Inject dependencies (dependency injection)
- No deep inheritance hierarchies
- Prefer "has-a" over "is-a"

**Pragmatic exception:** The following use single-level abstract classes for DRY boilerplate — acceptable as long as inheritance stays shallow (max 1 level):
- `BaseService<T>` — CRUD boilerplate for all entity services
- `ResourceAccessGuard` — authorization guard boilerplate
- `BaseWebhookService` (4 children) — HTTP webhook boilerplate (`contracts/services/base-webhook.service.ts`)
- `BaseMonatspreiseDirective` (3 children: RlmComponent, SlpComponent, SonderkundenComponent) — import page boilerplate (`frontend/crm-frontend/src/app/shared/directives/base-monatspreise.directive.ts`)

**Example:**
```typescript
// ❌ BAD: Deep inheritance hierarchy
class BaseService {
  constructor(protected db: Database) {}
}
class CRUDService extends BaseService {
  create() { /* ... */ }
  read() { /* ... */ }
}
class UserService extends CRUDService {
  /* ... */
}

// ✅ GOOD: Composition with dependency injection
interface Repository<T> {
  create(data: Partial<T>): Promise<T>;
  findById(id: string): Promise<T | null>;
}

class UserService {
  constructor(
    private readonly userRepository: Repository<User>,
    private readonly auditLogger: AuditLogger,
  ) {}

  async createUser(data: CreateUserDto): Promise<User> {
    const user = await this.userRepository.create(data);
    await this.auditLogger.log('USER_CREATED', user.id);
    return user;
  }
}
```

---

### 7. Law of Demeter (Principle of Least Knowledge)

**Rule:** Objects should only talk to their direct friends.

**In Practice:**
- Don't chain method calls through multiple objects
- Proper encapsulation
- No "train wrecks" (`a.b().c().d()`)

**Example:**
```typescript
// ❌ BAD: Law of Demeter violation
const city = user.getAddress().getCity().getName();

// ✅ GOOD: Ask the object to do it
const city = user.getCityName();

// Inside User class:
class User {
  getCityName(): string {
    return this.address.city.name;
  }
}
```

---

## 🏗️ Architecture Principles

### Clean/Hexagonal Architecture

**Rule:** Business logic should be independent of frameworks, UI, and infrastructure.

**Layers:**
1. **Domain** (Core) - Business logic, entities
2. **Application** - Use cases, services
3. **Infrastructure** - Database, external APIs
4. **Presentation** - Controllers, DTOs

**Dependencies flow inward:** Presentation → Application → Domain

**Example:**
```
src/
├── domain/
│   ├── entities/          # Pure business objects
│   └── interfaces/        # Contracts (repositories, etc.)
├── application/
│   └── services/          # Business logic, use cases
├── infrastructure/
│   ├── database/          # Database implementation
│   └── external/          # External API clients
└── presentation/
    └── controllers/       # HTTP handlers
```

---

### 12-Factor App Principles

**Rule:** Build cloud-native, scalable applications.

**Key Principles:**
1. ✅ **Codebase:** One codebase tracked in version control
2. ✅ **Dependencies:** Explicitly declared (package.json)
3. ✅ **Config:** Stored in environment variables (.env)
4. ✅ **Backing Services:** Attached resources (database, cache)
5. ✅ **Build/Release/Run:** Strict separation
6. ✅ **Processes:** Stateless, share-nothing
7. ✅ **Port Binding:** Self-contained services
8. ✅ **Concurrency:** Scale via process model
9. ✅ **Disposability:** Fast startup, graceful shutdown
10. ✅ **Dev/Prod Parity:** Keep environments similar
11. ✅ **Logs:** Treat as event streams (stdout)
12. ✅ **Admin Processes:** Run as one-off tasks

---

## 🔒 Security Principles

### Input Validation

**Rule:** All user input is hostile until proven otherwise.

**In Practice:**
- Validate at system boundaries (controllers)
- Use class-validator decorators
- Sanitize input
- Whitelist, don't blacklist

**Example:**
```typescript
// ✅ GOOD: Validated DTO
class CreateUserDto {
  @IsEmail()
  email: string;

  @IsStrongPassword()
  @MinLength(12)
  password: string;

  @IsString()
  @Length(2, 50)
  name: string;
}
```

---

### Explicit > Implicit

**Rule:** Be explicit in your code. No magic behavior.

**In Practice:**
- Clear function signatures with types
- Explicit error handling (no silent failures)
- Type annotations everywhere (TypeScript)
- Clear naming conventions

**Example:**
```typescript
// ❌ BAD: Implicit, unclear
function process(data: any) {
  // What does this return? When does it throw?
}

// ✅ GOOD: Explicit
async function processUserData(
  userId: string
): Promise<ProcessedUser | null> {
  // Clear what it does, returns, and when
}
```

---

### Validated Inputs, Actionable Errors, Structured Logs

**Rule:** Validate early, fail fast, log everything.

**Validated Inputs:**
```typescript
@Post('/users')
async createUser(@Body() dto: CreateUserDto) {
  // dto is validated by class-validator before this runs
}
```

**Actionable Errors:**
```typescript
// ❌ BAD: Unclear error
throw new Error('Failed');

// ✅ GOOD: Actionable error with context
throw new BadRequestException({
  message: 'Email address is already in use',
  field: 'email',
  suggestion: 'Try logging in or use password reset',
});
```

**Structured Logs:**
```typescript
// ✅ GOOD: Structured logging
this.logger.log({
  message: 'User created successfully',
  userId: user.id,
  email: user.email,
  correlationId: context.correlationId,
});
```

---

### No Secrets in Code or Logs

**Rule:** Never hardcode secrets. Never log secrets.

**In Practice:**
- All secrets in environment variables
- Secrets loaded from .env (development) or secret manager (production)
- Sanitize logs (no passwords, tokens, etc.)

**Example:**
```typescript
// ❌ BAD: Hardcoded secret
const apiKey = 'sk-1234567890abcdef';

// ✅ GOOD: Environment variable
const apiKey = process.env.API_KEY;
if (!apiKey) throw new Error('API_KEY not configured');

// ✅ GOOD: Sanitized logging
this.logger.log({
  message: 'API call made',
  endpoint: '/api/users',
  // Don't log the full request with auth headers!
});
```

---

### API Credentials in Integrations System

**Rule:** External API credentials belong in the Integrations system (`/verwaltung/integration`), NOT in environment variables.

**Why:**
- **Centralized Management:** All credentials in one UI, no scattered .env files
- **Auditability:** Changes are logged, credentials can be rotated via UI
- **Security:** Encrypted storage in DB via `INTEGRATION_ENCRYPTION_KEY`, not plaintext in .env files on disk
- **Transparency:** Rafael (and other team members) can see in the UI which integrations exist, what they do, and what the AI has configured — no hidden behavior
- **Consistency:** Same pattern for all external integrations

**Critical:** `INTEGRATION_ENCRYPTION_KEY` must be set in `.env` — it's the master key for encrypting/decrypting all integration credentials in the database. Without it, the Integrations module logs a warning and credential encryption is disabled.

**In Practice:**
- New integrations (APIs, webhooks, external services) → **always** create via Integrations module with proper name, description, and credentials
- Access credentials via `IntegrationsService.getCredentials(integrationId)`
- **Log all integration activity** — every credential access, API call, and configuration change must be traceable so the team knows what automated processes (including AI) are doing
- Environment variables only for infrastructure config (DB connection, Redis, ports)

**What goes WHERE:**

| Credential Type | Storage |
|-----------------|---------|
| External API keys (Montel, egON, etc.) | `crm.integrations` (DB, encrypted) |
| OAuth client credentials | `crm.integrations` (DB, encrypted) |
| Webhook secrets | `crm.integrations` (DB, encrypted) |
| `INTEGRATION_ENCRYPTION_KEY` | `.env` (infrastructure — encrypts the above) |
| Database connection string | `.env` (infrastructure) |
| JWT secret | `.env` (infrastructure) |
| Server ports | `.env` (infrastructure) |

**Example:**
```typescript
// ❌ BAD: API credentials in .env
const clientId = this.configService.get('MONTEL_CLIENT_ID');
const password = this.configService.get('MONTEL_PASSWORD');

// ✅ GOOD: API credentials from Integrations system
const integration = await this.integrationsService.findOne(integrationId);
const { clientId, username, password } = integration.credentials;
```

**Migration:** Existing integrations using .env (e.g., Montel, egON) should be migrated to use the Integrations system when touched.

---

### Fail Fast

**Rule:** Detect errors early and explicitly.

**In Practice:**
- Validate inputs at boundaries
- No swallowed exceptions
- Throw errors early
- Don't return null when you should throw

**Example:**
```typescript
// ❌ BAD: Silent failure
function getUser(id: string): User | null {
  try {
    return db.users.findById(id);
  } catch (error) {
    return null; // Swallowed error!
  }
}

// ✅ GOOD: Explicit error handling
async function getUser(id: string): Promise<User> {
  const user = await db.users.findById(id);
  if (!user) {
    throw new NotFoundException(`User ${id} not found`);
  }
  return user;
}
```

---

## 📚 Documentation Principles

### Documentation as Code

**Rule:** Documentation lives with code and is version controlled.

**In Practice:**
- JSDoc/TSDoc for public APIs
- README.md for modules
- Architecture diagrams in docs/
- ADRs for significant decisions

---

### Documentation Hygiene

**Rule:** Keep documentation minimal, focused, and up-to-date.

**Permanent Docs:**
- `README.md` - Overview, quickstart
- `CONTRIBUTING.md` - Development workflow
- `PRINCIPLES.md` - This file
- `docs/ARCHITEKTUR.md` - System design
- `docs/WissensDatenbank.md` - Knowledge base

**Transient Docs:**
- `/_ai/*.md` - Temporary task artifacts (deleted after consolidation)

**Policy:**
- ✅ Consolidate task artifacts to `docs/WissensDatenbank.md`
- ✅ Update `docs/ARCHITEKTUR.md` when architecture changes
- 🗑️ Delete redundant/outdated .md files
- 📦 Archive valuable old docs to `docs/archive/`

---

## ✅ Testing Principles

### Test Pyramid

**Rule:** More unit tests, fewer integration tests, even fewer E2E tests.

```
       /\
      /  \     E2E Tests (Few)
     /----\
    /      \   Integration Tests (Some)
   /--------\
  /          \ Unit Tests (Many)
 /____________\
```

**Coverage Targets:**
- **Unit Tests:** 80%+ for new code
- **Integration Tests:** Key flows
- **E2E Tests:** Critical user journeys

---

### Test Quality

**Rule:** Tests should be readable, independent, and deterministic.

**Characteristics:**
- ✅ **Readable:** Clear test names, arrange/act/assert
- ✅ **Independent:** No shared state between tests
- ✅ **Deterministic:** Same input = same output (no flaky tests)
- ✅ **Fast:** Unit tests run in milliseconds
- ✅ **Realistic:** Test data resembles production data

**Example:**
```typescript
describe('UserService', () => {
  describe('createUser', () => {
    it('should create a user with hashed password', async () => {
      // Arrange
      const dto = { email: 'test@example.com', password: 'Test123!@#' };
      const mockRepository = createMockRepository();

      // Act
      const user = await service.createUser(dto);

      // Assert
      expect(user.email).toBe(dto.email);
      expect(user.password).not.toBe(dto.password); // Hashed
      expect(mockRepository.create).toHaveBeenCalledTimes(1);
    });

    it('should throw BadRequestException for duplicate email', async () => {
      // Arrange
      const dto = { email: 'existing@example.com', password: 'Test123!@#' };
      mockRepository.findByEmail.mockResolvedValue(existingUser);

      // Act & Assert
      await expect(service.createUser(dto))
        .rejects
        .toThrow(BadRequestException);
    });
  });
});
```

---

## 🚀 Performance Principles

### Premature Optimization is Evil

**Rule:** Make it work, make it right, make it fast (in that order).

**In Practice:**
- Optimize only when there's a proven performance problem
- Measure first (profiling, benchmarks)
- Focus on algorithmic complexity (O(n) vs O(n²))
- Avoid micro-optimizations

---

### Performance Safeguards

**In Practice:**
- Paginate large datasets
- Index database queries appropriately
- Avoid N+1 queries
- Use caching strategically
- Set timeouts on external calls

**Example:**
```typescript
// ✅ GOOD: Pagination
@Get('/users')
async getUsers(
  @Query('page', ParseIntPipe) page = 1,
  @Query('limit', ParseIntPipe) limit = 20,
) {
  return this.userService.findAll({ page, limit });
}
```

---

## 🔄 Refactoring Principles

### Refactor Regularly

**Rule:** Leave the code better than you found it.

**When to Refactor:**
- When you touch code that's hard to understand
- When you see duplication
- When tests are hard to write
- When adding a feature feels harder than it should

**When NOT to Refactor:**
- When deadlines are tight (add TODO instead)
- When you don't understand the code yet
- When there are no tests (add tests first)

---

## 🛡️ Code Review Principles

### Self-Review First

**Rule:** Review your own code before asking others.

**Checklist:**
- [ ] KISS, DRY, YAGNI, SRP followed
- [ ] Security checklist passed
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No debug code or console.logs
- [ ] Linter and type checker pass

---

## 🎨 Style Principles

### Consistency > Preference

**Rule:** Follow the project's existing style, even if you prefer another.

**In Practice:**
- Use ESLint + Prettier (configured)
- TypeScript strict mode
- Conventional commit messages
- Consistent naming conventions

### Color Usage

**Rule:** ALWAYS use CSS variables for colors — NEVER hardcode hex values.

**Brand colors are dynamic** — they are configured via the Branding Settings page (`/branding`) and stored in the database. There are no fixed "SGB colors". The current defaults happen to be `#8bb23f` (primary) and `#22304a` (secondary), but tenants can change them at any time.

**In Practice:**
- **CSS/SCSS:** Use `var(--theme-primary)` / `var(--theme-secondary)` — values are set at runtime by `BrandingService`
- **TypeScript:** Use `DEFAULT_PRIMARY` / `DEFAULT_SECONDARY` from `shared/constants/colors.ts` only as fallback defaults, never as "the" brand color
- **Never assume** a specific hex value is "the brand color" — it's whatever the tenant configured

**Pragmatic exceptions (hex literals allowed):**
- CSS `var()` fallback values: `var(--theme-primary, #8bb23f)` — correct pattern
- Email HTML templates: raw HTML sent via email cannot use CSS variables or TS constants
- Third-party brand colors: provider-specific colors (OpenAI green, Azure blue) are config data
- Chart/palette colors: non-brand colors in chart datasets, role badges, status indicators
- Test files: test data clarity takes priority over DRY

### Visual Design Reference: Marketing Page

**Rule:** When building or updating UI, orient the visual design on the Marketing page (`/marketing`).

**In Practice:**
- The Marketing page is the design reference for layout, spacing, card styles, table styling, and overall look & feel
- New pages should match the Marketing page's visual patterns (card headers, filter bars, action buttons, modals)
- When in doubt about how something should look, check the Marketing page first

---

## 📊 Monitoring & Observability

### Log Everything Important

**Rule:** You can't debug what you can't see.

**What to Log:**
- ✅ Authentication events
- ✅ Authorization failures
- ✅ Errors and exceptions
- ✅ External API calls
- ✅ Database queries (slow queries)
- ✅ Business-critical actions

**What NOT to Log:**
- ❌ Passwords or secrets
- ❌ Personal data (GDPR)
- ❌ Full request/response bodies (unless debug mode)

---

## 🎯 Summary

**Core Principles:**
1. **KISS** - Simple > Clever
2. **DRY** - Don't Repeat Knowledge
3. **YAGNI** - Build What You Need Now
4. **SRP** - One Responsibility Per Component
5. **High Cohesion / Low Coupling** - Related Together, Minimal Dependencies
6. **Composition > Inheritance** - Flexible > Rigid
7. **Law of Demeter** - Talk to Friends Only

**Architecture:**
- Clean/Hexagonal Architecture
- 12-Factor App Principles

**Security:**
- Validate All Inputs
- Explicit Error Handling
- No Secrets in Code/Logs
- Fail Fast

**Documentation:**
- Documentation as Code
- Minimal, Focused, Up-to-date
- Consolidate & Clean Up

**Testing:**
- Test Pyramid (Many Unit, Some Integration, Few E2E)
- 80%+ Coverage for New Code
- Readable, Independent, Deterministic

**Performance:**
- Measure Before Optimizing
- Algorithmic Efficiency > Micro-optimizations
- Pagination, Indexing, Caching

**Process:**
- Self-Review First
- Refactor Regularly
- Consistency > Preference
- Log Everything Important

---

**Remember:** These are guidelines, not laws. Use judgment. The goal is **maintainable, evolvable, documented code** - not perfect code.

---

**Last Updated:** 2026-03-12
**Maintainer:** Konrad Reyhe
