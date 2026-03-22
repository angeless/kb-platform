# KB Platform Frontend Audit Report

**Date:** March 22, 2026
**Version Analyzed:** v0.25.0
**Scope:** `/apps/web/src` (1,603 LOC across TypeScript/TSX)
**Framework:** Next.js 15, React 19, TypeScript

---

## Executive Summary

The KB Platform frontend is a **production-ready SPA** with solid foundational architecture, but has **critical gaps in production readiness** and several **moderate security/UX concerns** that must be addressed before public deployment. The codebase demonstrates good engineering practices (error handling, state management, API abstraction) but lacks comprehensive feature coverage, accessibility standards, and edge case handling in key workflows.

**Overall Risk Level:** MEDIUM-HIGH
**Recommendation:** Address critical issues before v1.0 release.

---

## 1. CRITICAL ISSUES (MUST FIX)

### 1.1 Syntax Error in forgot-password/page.tsx

**Location:** `/src/app/forgot-password/page.tsx` lines 134-136

**Issue:** Duplicate closing JSX tag causing parsing error:
```tsx
// Line 133-136 - MALFORMED
</div>
  );
}
div>
  );
}
```

**Impact:** Page will fail to compile/render. Users cannot access password recovery flow.
**Fix Priority:** CRITICAL (P0)
**Solution:** Remove duplicate closing tags (lines 134-136).

---

### 1.2 Insecure Token Handling in forgot-password/page.tsx

**Location:** `/src/app/forgot-password/page.tsx` lines 33-66

**Issue:** Reset token is exposed in frontend UI during development mode:
```tsx
{resetToken && (
  <div className="mb-6 rounded-lg bg-yellow-50 p-3 text-sm">
    <p className="font-medium text-yellow-800">开发模式 — 重置 Token:</p>
    <p className="mt-1 break-all font-mono text-xs text-yellow-700">
      {resetToken}
    </p>
```

**Security Concerns:**
- Token is visible in browser DOM, can be captured via XSS
- Token appears in browser history
- No rate limiting on token extraction
- Token displayed in plain text, not masked

**Impact:** Attackers could:
- Steal password reset tokens from user browsers
- Reset arbitrary user passwords if token is intercepted
- Perform account takeovers

**Fix Priority:** CRITICAL (P0)
**Solutions:**
1. Remove development mode token display from production
2. Use environment flag: `if (process.env.NODE_ENV !== 'production') { ... }`
3. Link instead of displaying raw token: `<a href="/reset-password?token=${resetToken}">Click here to reset</a>`
4. Log token server-side only, never expose to frontend

---

### 1.3 No Login Session Validation on Initial Load

**Location:** `/src/app/(dashboard)/layout.tsx` lines 25-32

**Issue:** Dashboard layout checks `localStorage` instead of using auth store state:
```tsx
useEffect(() => {
  if (user === null && typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
    }
  }
}, [user, router]);
```

**Problems:**
- Code reads `access_token` from `localStorage` but auth-store never writes to it
- Token is stored in httpOnly cookies by backend, not localStorage
- This check is dead code—never executes correctly
- User could be logged out (null) but still see loading skeleton indefinitely
- Race condition: user could navigate to protected routes before auth check completes

**Impact:**
- Logged-out users might briefly see dashboard content before redirect
- Stale state in auth store isn't refreshed on new sessions
- False sense of security from a check that doesn't work

**Fix Priority:** CRITICAL (P0)
**Solutions:**
1. Remove `localStorage` check—rely only on `useAuthStore` state
2. Call `checkAuth()` on mount to validate session with backend
3. Wait for auth check to complete before rendering dashboard
4. Add explicit loading gate:
```tsx
if (!user && isLoading) return <SkeletonList />; // still checking
if (!user && !isLoading) return null; // redirect happens in effect
```

---

### 1.4 No CSRF Protection

**Location:** Global issue across `/src/lib/api.ts`

**Issue:** All POST/PUT/PATCH requests lack CSRF token headers:
```tsx
async request<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  // No CSRF token added here
  headers["Content-Type"] = "application/json";
```

**Attack Vector:**
- Attacker can create malicious form that POSTs to `/v1/projects` to create projects in victim's account
- Attacker can POST to `/v1/docs/${docId}/publish` to publish documents
- Attacker can delete users, change settings, etc.

**Impact:** High-severity CSRF attacks on state-changing operations.

**Fix Priority:** CRITICAL (P0)
**Solutions:**
1. Backend should use SameSite=Strict cookie flag for auth token
2. Frontend should send CSRF token in X-CSRF-Token header:
```tsx
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
if (csrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method || 'GET')) {
  headers["X-CSRF-Token"] = csrfToken;
}
```
3. HTML layout should include: `<meta name="csrf-token" content="..." />`

---

### 1.5 XSS Vulnerability in Document Edit Modal

**Location:** `/src/app/(dashboard)/projects/[id]/search/page.tsx` lines 164-166

**Issue:** QA answer is rendered with `whitespace-pre-wrap` without sanitization:
```tsx
<div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
  {qaAnswer.answer}
</div>
```

**Vulnerability:** If backend returns HTML in QA answer, it renders raw HTML:
- `<img src=x onerror="alert('xss')">` will execute
- React's JSX doesn't sanitize string content by default
- markdown-view component uses `rehypeSanitize` but this doesn't

**Impact:** Stored XSS if AI model or backend injection occurs.

**Fix Priority:** CRITICAL (P0)
**Solution:** Always sanitize user-controlled content:
```tsx
import DOMPurify from 'dompurify';

<div dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(qaAnswer.answer)}} />
```
Or better: wrap in `MarkdownView` component which already sanitizes.

---

## 2. HIGH PRIORITY ISSUES (BLOCKING PRODUCTION)

### 2.1 Incomplete Register Flow

**Location:** `/src/app/register/page.tsx` lines 42-47

**Issue:** Registration doesn't auto-login user; requires manual login:
```tsx
try {
  await register(tenantName, email, password);
  router.push("/projects");  // ❌ Redirects WITHOUT checking if logged in
} catch {
  // error is set in store
}
```

And in `useAuthStore`:
```tsx
register: async (tenantName, email, password) => {
  // ... calls API
  set({ isLoading: false });
  // ❌ Does NOT set user in state
  // ❌ Does NOT auto-login
}
```

**Issues:**
- After registration, user is NOT logged in
- User is redirected to `/projects` but not authenticated
- Dashboard redirects user back to login, creating confusion
- No success message or confirmation

**User Impact:** New users complete registration but can't access the system; must log in again.

**Fix Priority:** HIGH (P1)
**Solution:**
```tsx
register: async (tenantName, email, password) => {
  set({ isLoading: true, error: null });
  try {
    await api.post("/v1/auth/register", { tenant_name: tenantName, email, password });
    // THEN auto-login
    await api.post("/v1/auth/login", { email, password });
    const meResp = await api.get<User>("/v1/auth/me");
    set({ user: meResp.data, isLoading: false });
  } catch (e) {
    const msg = e instanceof ApiClientError ? e.message : "注册失败";
    set({ error: msg, isLoading: false });
    throw e;
  }
}
```

---

### 2.2 No File Upload Validation

**Location:** `/src/components/file-upload.tsx` lines 65-80

**Issue:** No client-side file validation before upload:
```tsx
const handleFiles = useCallback(
  async (files: FileList | File[]) => {
    const newItems: UploadItem[] = Array.from(files).map((file) => ({
      file,
      status: "pending" as const,
      progress: 0,  // ❌ No size check
    }));                  // ❌ No type check
```

**Problems:**
- Users can upload 10GB files, waste bandwidth, hit server limits
- Users can upload executable files (.exe, .sh) if backend allows
- No progress feedback for large files
- No retry mechanism on network failure during upload
- Upload state is lost on page refresh (in-progress uploads disappear)

**Impact:**
- Poor user experience with large files
- Wasted bandwidth
- Potential security issue if backend doesn't validate

**Fix Priority:** HIGH (P1)
**Solutions:**
```tsx
const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB
const ALLOWED_TYPES = ['pdf', 'image', 'audio', 'doc', 'text', 'zip'];

const handleFiles = useCallback(async (files: FileList | File[]) => {
  const validFiles = Array.from(files).filter(file => {
    if (file.size > MAX_FILE_SIZE) {
      setError(`文件 ${file.name} 超过 500MB 限制`);
      return false;
    }
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_TYPES.includes(guessType(file.name))) {
      setError(`不支持的文件类型：${ext}`);
      return false;
    }
    return true;
  });
  // ... rest of code
}, [items.length, projectId, onUploadComplete]);
```

---

### 2.3 Error Toast Global State Design Flaw

**Location:** `/src/components/error-toast.tsx` lines 11-21

**Issue:** Toast system uses mutable global variable instead of React context:
```tsx
let addToastFn: ((message: string, type?: Toast["type"]) => void) | null = null;

export function showErrorToast(message: string, type: Toast["type"] = "error") {
  if (addToastFn) {
    addToastFn(message, type);  // ❌ Can be null
  }
}
```

**Problems:**
- `addToastFn` can be null if ToastContainer hasn't mounted yet
- Silent failures if called before container mounts
- No error tracking
- API client error toasts might not show
- React SSR incompatible—unmounting/remounting resets the function

**Impact:**
- Error messages silently disappear
- Users unaware of failures
- Difficult to debug when toasts don't appear

**Fix Priority:** HIGH (P1)
**Solution:** Use React Context instead:
```tsx
import { createContext, useContext, ReactNode } from "react";

interface ToastContextType {
  showToast: (message: string, type: "error" | "warning" | "info") => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = (message: string, type: "error" | "warning" | "info" = "error") => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <ToastRenderer toasts={toasts} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
```

---

### 2.4 Unsaved Changes Detection Only on Edit Page

**Location:** `/src/app/(dashboard)/docs/[id]/edit/page.tsx` lines 56-65

**Issue:** Only warns on beforeunload but doesn't prevent soft navigation:
```tsx
useEffect(() => {
  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (content !== initialContentRef.current) {
      e.preventDefault();
      e.returnValue = "";
    }
  };
  window.addEventListener("beforeunload", handleBeforeUnload);
  return () => window.removeEventListener("beforeunload", handleBeforeUnload);
}, [content]);
```

**Problems:**
- `beforeunload` only fires for page refresh/close, not Next.js navigation
- User can click back button without warning
- Unsaved changes lost silently
- Line 91 shows a `confirm()` dialog manually, but it's easy to miss

**Impact:** Users lose edits when navigating away via Next.js Link/router.

**Fix Priority:** HIGH (P1)
**Solution:** Add router change interceptor:
```tsx
useEffect(() => {
  const handleRouteChange = () => {
    if (isDirty && !window.confirm("有未保存的修改，确定离开吗？")) {
      throw new Error("Route change aborted by user");
    }
  };

  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (isDirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  };

  router.beforePopState(({ url }) => {
    if (isDirty) {
      return window.confirm("有未保存的修改，确定离开吗？");
    }
    return true;
  });

  window.addEventListener("beforeunload", handleBeforeUnload);
  return () => window.removeEventListener("beforeunload", handleBeforeUnload);
}, [isDirty, router]);
```

---

### 2.5 Search Result Pagination Missing

**Location:** `/src/app/(dashboard)/projects/[id]/search/page.tsx` lines 211-273

**Issue:** Search results don't have pagination; only first N results shown:
```tsx
{mode === "hybrid" && (
  <>
    <p className="mb-3 text-sm text-gray-500">找到 {total} 条结果</p>
    <div className="space-y-3">
      {hybridResults.map((hit) => (
        // ... renders all results from API
      ))}
    </div>
  </>
)}
```

**Problems:**
- If search returns 1000+ results, all rendered at once → performance hit
- No way to navigate to page 2, 3, etc.
- Similar issue in assets page pagination doesn't exist in search
- User can't find specific results in large result sets

**Impact:** Poor performance with large datasets; broken search experience.

**Fix Priority:** HIGH (P1)
**Solution:** Add pagination controls (similar to assets page):
```tsx
const [page, setPage] = useState(1);
const pageSize = 20;
const totalPages = Math.ceil(total / pageSize);

// In search handler, pass page param to API
const resp = await api.post<HybridHit[]>("/v1/search/hybrid", {
  project_id: projectId,
  query: q,
  page,
  page_size: pageSize,
});

// Add pagination UI after results
{totalPages > 1 && (
  <div className="mt-4 flex items-center justify-center gap-2">
    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
      上一页
    </button>
    <span>{page} / {totalPages}</span>
    <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
      下一页
    </button>
  </div>
)}
```

---

## 3. MODERATE PRIORITY ISSUES (SHOULD FIX BEFORE V1.0)

### 3.1 Missing Error Boundaries for List Pages

**Location:** Project list, assets, users, audit pages lack error boundaries

**Issue:** If API fails or component errors, entire page crashes instead of showing error:
```tsx
// /src/app/(dashboard)/projects/page.tsx
export default function ProjectsPage() {
  const { data, isLoading, error } = useProjects();
  // Only shows error message, doesn't catch render errors
  if (!data) return <div>Loading...</div>;

  return (
    // If map() throws, whole page crashes
    <div className="grid gap-4">{projects.map((p) => ...)}</div>
  );
}
```

**Impact:** One corrupted project in list breaks entire projects page.

**Fix Priority:** MEDIUM (P2)
**Solution:** Wrap with error boundary:
```tsx
import { ErrorBoundary } from "@/components/error-boundary";

export default function ProjectsPage() {
  return (
    <ErrorBoundary>
      {/* existing code */}
    </ErrorBoundary>
  );
}
```

---

### 3.2 No Loading Placeholder in List Tables

**Location:** All table pages (users, assets, audit-logs)

**Issue:** While loading, shows "加载中..." text instead of skeleton:
```tsx
{isLoading ? (
  <div className="py-12 text-center text-gray-400">加载中...</div>
) : (
  <table>...</table>
)}
```

**Problems:**
- Layout shift when table appears
- No visual skeleton to show where content will be
- Poor perceived performance

**Impact:** Bad user experience during initial page load.

**Fix Priority:** MEDIUM (P2)
**Solution:** Create table skeleton:
```tsx
function TableSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-200 bg-gray-50">
          <tr>
            <th className="px-5 py-3 h-10 bg-gray-100" />
            <th className="px-5 py-3 h-10 bg-gray-100" />
            <th className="px-5 py-3 h-10 bg-gray-100" />
          </tr>
        </thead>
        <tbody>
          {Array(5).fill(0).map((_, i) => (
            <tr key={i} className="border-b border-gray-100">
              <td className="px-5 py-3"><div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" /></td>
              {/* ... repeat for each column */}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Usage
{isLoading ? <TableSkeleton /> : <table>...</table>}
```

---

### 3.3 No Confirmation Dialog for Destructive Actions

**Location:** Project list, users, docs pages lack delete confirmations

**Issue:** No delete functionality visible, but if added would lack safeguards:
```tsx
// Hypothetical delete—currently missing
async function handleDelete() {
  await api.del(`/v1/projects/${projectId}`);  // ❌ No confirmation
}
```

**Problems:**
- Accidental clicks delete data
- No way to undo
- No confirmation message

**Impact:** Data loss from misclicks.

**Fix Priority:** MEDIUM (P2)
**Solution:** Use ConfirmDialog (already exists):
```tsx
const [deleteConfirm, setDeleteConfirm] = useState(false);

<ConfirmDialog
  open={deleteConfirm}
  title="删除项目"
  message="确定要删除此项目及其所有资料吗？此操作不可撤销。"
  confirmText="删除"
  cancelText="取消"
  onConfirm={async () => {
    await api.del(`/v1/projects/${projectId}`);
    router.push("/projects");
  }}
  onCancel={() => setDeleteConfirm(false)}
/>

<button onClick={() => setDeleteConfirm(true)} className="text-red-600">
  删除项目
</button>
```

---

### 3.4 No Timezone Handling

**Location:** Global issue: all date displays use `toLocaleDateString("zh-CN")`

**Issue:** Assumes user's browser timezone; doesn't show timezone info:
```tsx
<td className="px-5 py-3 text-gray-400">
  {new Date(asset.uploaded_at).toLocaleDateString("zh-CN")}
</td>
```

**Problems:**
- User in NYC sees upload timestamp in their timezone, but doesn't know if backend timestamp was in UTC or EST
- No timezone indicator shown
- Full timestamp (including time) is missing in some places
- API likely returns UTC ISO strings; frontend doesn't clarify

**Impact:** Confusion about when assets were uploaded, especially for distributed teams.

**Fix Priority:** MEDIUM (P2)
**Solution:**
```tsx
// src/lib/date-format.ts
export function formatDateTime(isoString: string, showTime = true) {
  const date = new Date(isoString);
  const formatter = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: showTime ? "2-digit" : undefined,
    minute: showTime ? "2-digit" : undefined,
    timeZoneName: "short",
  });
  return formatter.format(date);
}

// Usage
{formatDateTime(asset.uploaded_at, true)}
// Output: "2026-03-22 14:30 GMT+8"
```

---

### 3.5 No Keyboard Navigation Support

**Location:** Modal dialogs, forms

**Issue:** Users cannot close modals with Escape key:
```tsx
// /src/components/confirm-dialog.tsx
export function ConfirmDialog({ open, ... }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex..." role="dialog">
      {/* No Escape handler */}
    </div>
  );
}
```

**Problems:**
- Power users can't use familiar Escape key to close
- Tab order not managed (can tab to elements behind modal)
- No announcement to screen readers that modal is open

**Impact:** Worse accessibility, especially for keyboard-only users.

**Fix Priority:** MEDIUM (P2)
**Solution:**
```tsx
useEffect(() => {
  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === "Escape" && open) {
      onCancel();
    }
  };
  window.addEventListener("keydown", handleEscape);
  return () => window.removeEventListener("keydown", handleEscape);
}, [open, onCancel]);

// Also wrap in FocusTrap
import { createPortal } from 'react-dom';

return createPortal(
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
       role="dialog"
       aria-modal="true">
    {/* content with focus trap */}
  </div>,
  document.body
);
```

---

## 4. ACCESSIBILITY ISSUES

### 4.1 Missing ARIA Labels

**Locations:** Multiple components

**Issue:** Status badges have no accessible labels:
```tsx
// /src/components/status-badge.tsx
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = STATUS_LABELS[status] || status;
  return (
    <span className={...} aria-label={`状态：${label}`}>
      {label}
    </span>
  );
}
```

**What's good:** `aria-label` is present.

**What's missing:**
- Form inputs don't have associated `<label>` elements with `htmlFor`
- Buttons like "上传资料" and "新建项目" use icon-only styling in some views
- No `aria-live` regions for async updates (search results, file upload progress)
- Status badges in tables not marked as headers

**Impact:** Screen reader users can't navigate or understand content properly.

**Fix Priority:** MEDIUM (P2)
**Audit findings:**
```tsx
// ❌ BAD: Label not associated
<div>
  <label className="mb-1 block text-sm font-medium text-gray-700">邮箱</label>
  <input type="email" ... />
</div>

// ✓ GOOD: Proper association
<div>
  <label htmlFor="email-input" className="mb-1 block text-sm font-medium text-gray-700">
    邮箱
  </label>
  <input id="email-input" type="email" ... />
</div>
```

---

### 4.2 No Focus Indicators

**Location:** All interactive elements

**Issue:** Removed focus outlines might break keyboard navigation:
```tsx
// tailwindcss focus rules exist but might be overridden
className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
```

**Problems:**
- `focus:outline-none` removes default outline
- `focus:ring-1` adds ring but might be insufficient
- Links don't have visible focus states
- Sidebar nav items might not show focus

**Impact:** Keyboard users can't tell which element has focus.

**Fix Priority:** MEDIUM (P2)
**Solution:** Ensure all focusable elements have clear focus:
```tsx
// Global CSS
:focus-visible {
  outline: 2px solid var(--color-primary-600);
  outline-offset: 2px;
}

// Or in Tailwind
className="... focus-visible:outline-2 focus-visible:outline-primary-600 focus-visible:outline-offset-2"
```

---

### 4.3 Insufficient Color Contrast

**Location:** Status badges and gray text

**Issue:** Many gray text elements may fail WCAG AA contrast:
```tsx
<p className="text-gray-400">创建于 ...</p>  // gray-400 = #9ca3af
<span className="text-gray-500">已禁用</span>  // gray-500 = #6b7280
```

**Contrast ratio check:**
- gray-400 on white: ~4.5:1 (barely passes AA for small text)
- gray-500 on white: ~6.5:1 (passes AA)
- Some disabled states might be <3:1 (fails WCAG)

**Impact:** Users with low vision can't read some content.

**Fix Priority:** MEDIUM (P2)
**Solution:** Use higher contrast colors for important text:
```tsx
// Instead of gray-400 (weak contrast), use gray-600
<p className="text-gray-600">创建于 ...</p>
```

---

## 5. MISSING FEATURES FOR PRODUCTION

### 5.1 No Pagination in QA Answer Sources

**Location:** `/src/app/(dashboard)/projects/[id]/search/page.tsx` lines 169-189

**Issue:** If QA returns 100+ sources, all rendered at once.

**Current:**
```tsx
{qaAnswer.sources.map((src) => (
  <Link key={src.doc_id} href={...} className="...">
    {src.title}
  </Link>
))}
```

**Fix:** Add pagination to sources list similar to search results.

---

### 5.2 No Loading Progress for Long Operations

**Location:** All async operations

**Issue:** Users don't know if app is still working:
```tsx
const [searching, setSearching] = useState(false);

{searching ? "搜索中..." : mode === "qa" ? "提问" : "搜索"}
```

**What's missing:**
- Progress bar for long operations
- Estimated time remaining
- Ability to cancel operations (file upload has this, but search doesn't)
- Optimistic UI updates (don't wait for server)

**Impact:** User thinks app is frozen.

**Fix Priority:** MEDIUM (P2)

---

### 5.3 No Search Query Suggestions/Autocomplete

**Location:** `/src/app/(dashboard)/projects/[id]/search/page.tsx` line 136

**Issue:** Search input has no autocomplete, suggestions, or recent searches:
```tsx
<input
  type="text"
  value={query}
  onChange={(e) => setQuery(e.target.value)}
  placeholder="..."
/>
```

**What's missing:**
- Recent searches cache
- Suggested queries based on document titles
- Debounced live search
- Search history in localStorage

**Impact:** Worse search experience; users must type full queries.

**Fix Priority:** LOW (P3) — nice to have

---

### 5.4 No Export/Download Functionality

**Location:** Project has `/projects/[id]/exports` route but no UI implementation

**Issue:** `exports` page is mentioned but not shown in screenshots.

**Impact:** Users can't get data out of the system.

---

### 5.5 No Project Settings Page Implementation

**Location:** `/src/app/(dashboard)/projects/[id]/settings/page.tsx` not provided

**Issue:** Settings page referenced in UI but implementation not in scope.

---

## 6. STATE MANAGEMENT & DATA FLOW ISSUES

### 6.1 Auth Store Doesn't Persist Across Page Reloads

**Location:** `/src/stores/auth-store.ts`

**Issue:** User state is lost on page reload:
```tsx
const useAuthStore = create<AuthState>((set) => ({
  user: null,  // ❌ Always starts as null
  // ...
}));
```

**Current workaround:** Dashboard layout calls `checkAuth()` on mount. But this creates a flash of loading state.

**Fix Priority:** MEDIUM (P2)
**Solutions:**
1. Use `localStorage` to persist user object (not tokens):
```tsx
// In zustand create function
initialize: async () => {
  const stored = localStorage.getItem("user");
  if (stored) {
    set({ user: JSON.parse(stored) });
  }
  // Still verify with backend
  try {
    const resp = await api.get<User>("/v1/auth/me");
    set({ user: resp.data });
    localStorage.setItem("user", JSON.stringify(resp.data));
  } catch {
    set({ user: null });
    localStorage.removeItem("user");
  }
}
```

2. Or use `hydrate` option in zustand to pre-populate state from sessionStorage.

---

### 6.2 Query Client Not Configured for Error Handling

**Location:** `/src/components/providers.tsx` lines 9-16

**Issue:** React Query has minimal configuration:
```tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: 1,
    },
  },
});
```

**Missing:**
- `onError` callback to show error toasts
- `onSuccess` callback for side effects
- `gcTime` (garbage collection) configuration
- Retry strategy doesn't account for 401s
- No mutation error handling

**Impact:** Errors aren't surfaced to user; retry logic is basic.

**Fix Priority:** MEDIUM (P2)

---

## 7. MOBILE & RESPONSIVE DESIGN ISSUES

### 7.1 Search Result Cards Don't Wrap on Mobile

**Location:** `/src/app/(dashboard)/projects/[id]/search/page.tsx` lines 223-237

**Issue:** Status badge, doc type, and match type badges might overflow on small screens:
```tsx
<div className="flex items-center gap-3">
  <h3 className="font-semibold text-gray-900">{hit.title}</h3>
  <StatusBadge status={hit.status} />
  <span className="text-xs text-gray-400">...</span>
  <span className={`rounded-full px-2 py-0.5 text-xs ${matchInfo.color}`}>
    {matchInfo.label}
  </span>
</div>
```

**Problem:** On mobile, badges push title off screen.

**Fix:**
```tsx
<div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-3">
  <h3 className="font-semibold text-gray-900 flex-1 break-words">{hit.title}</h3>
  <div className="flex flex-wrap gap-1">
    <StatusBadge status={hit.status} />
    <span className="text-xs text-gray-400">...</span>
    <span className={`rounded-full px-2 py-0.5 text-xs ${matchInfo.color}`}>
      {matchInfo.label}
    </span>
  </div>
</div>
```

---

### 7.2 Form Inputs Don't Stack on Mobile

**Location:** Projects assets page, invite users form

**Issue:** Some forms have side-by-side inputs that don't stack on mobile.

---

## 8. PERFORMANCE CONCERNS

### 8.1 No Image Optimization

**Location:** No images currently in codebase (using emoji), but architecture mentions assets

**Note:** When adding images (project logos, thumbnails), ensure:
- Use `next/image` component for auto-optimization
- Lazy load images below fold
- Provide `alt` text for accessibility

---

### 8.2 No Code Splitting for Heavy Components

**Location:** `/src/components/markdown-view.tsx` imports `react-markdown` and `rehype-sanitize`

**Issue:** `react-markdown` (~50KB) is loaded on every page.

**Fix:** Use dynamic imports for heavy components:
```tsx
import dynamic from "next/dynamic";

const MarkdownView = dynamic(() => import("@/components/markdown-view"), {
  loading: () => <div className="h-64 bg-gray-200 animate-pulse" />,
});
```

---

### 8.3 React Query Stale Time Too Short

**Location:** `/src/components/providers.tsx` line 12

**Issue:** `staleTime: 30 * 1000` means data refreshes every 30 seconds:
```tsx
queries: {
  staleTime: 30 * 1000, // ❌ Aggressive refresh
}
```

**Problem:** Causes unnecessary API calls and poor offline support.

**Fix:** Use longer stale times:
```tsx
queries: {
  staleTime: 5 * 60 * 1000, // 5 minutes
  gcTime: 10 * 60 * 1000,   // 10 minutes (formerly cacheTime)
}
```

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Hardcoded API_BASE in Multiple Files

**Location:** `/src/app/forgot-password/page.tsx` line 6, `/src/app/reset-password/page.tsx` line 7

**Issue:** API URL is duplicated instead of centralized:
```tsx
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

**Problem:** Should use API client instead.

**Fix:** Use api client from `lib/api.ts`.

---

### 9.2 No Input Sanitization in Forms

**Location:** All forms use controlled inputs without sanitization

**Issue:** User input is passed directly to API:
```tsx
<input
  type="text"
  value={newName}
  onChange={(e) => setNewName(e.target.value)}
/>

// Later:
await createProject.mutateAsync({ name: newName, ... });
```

**Problem:** XSS isn't an issue because API likely validates, but frontend should also trim/validate.

**Fix:**
```tsx
<input
  type="text"
  value={newName.trim()}
  onChange={(e) => setNewName(e.target.value)}
  maxLength={255}
/>
```

---

### 9.3 No Rate Limiting on Frontend

**Location:** All API calls

**Issue:** Users can spam buttons to create multiple requests:
```tsx
<button
  onClick={() => setShowCreate(!showCreate)}
  className="..."
>
  新建项目
</button>
```

**Problem:** No debounce; user can click 10 times before request returns.

**Fix:** Use `pending` state:
```tsx
<button
  onClick={() => setShowCreate(!showCreate)}
  disabled={createProject.isPending}
>
  {createProject.isPending ? "创建中..." : "新建项目"}
</button>
```

---

## 10. TESTING GAPS

### 10.1 Low Test Coverage

**Location:** `/src/__tests__/` has only 8 test files for ~1,600 LOC

**Coverage:**
- `lib/api.ts`: ✓ Good coverage with auth/refresh tests
- Components: Partial (error-boundary, markdown-view, status-badge, tree-node)
- Pages: ❌ ZERO tests
- Hooks: ❌ ZERO tests
- Auth store: ❌ ZERO tests
- Complex flows: ❌ No integration tests

**Issue:** Critical business logic has no tests:
- Login/register flows
- Document editing with unsaved changes
- File upload with progress
- Search with different modes

**Fix Priority:** MEDIUM (P2)
**Recommendation:** Add tests for:
1. Auth store (login, register, logout, refresh)
2. Document edit page (unsaved changes, save, navigation)
3. File upload (progress, cancellation, error handling)
4. Search page (mode switching, pagination, API errors)

---

## 11. DOCUMENTATION GAPS

### 11.1 No Component Documentation

**Issue:** No Storybook or component docs.

**Recommendation:** Add JSDoc comments to all exported components:
```tsx
/**
 * Status badge component
 * @param {string} status - Technical status value (e.g., "draft", "published")
 * @param {string} [className] - Additional CSS classes
 * @returns {React.ReactElement}
 */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  // ...
}
```

---

### 11.2 No API Integration Documentation

**Issue:** How to add new API endpoints? No guide.

**Recommendation:** Create `API_INTEGRATION.md`:
```md
# Adding New API Endpoints

1. Define types in hook: `src/hooks/useMyFeature.ts`
2. Use React Query `useQuery` or `useMutation`
3. Call via `api.get()`, `api.post()`, etc.
4. Errors automatically caught and shown as toasts

Example:
\`\`\`tsx
export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del(`/v1/projects/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });
}
\`\`\`
```

---

## 12. BROWSER COMPATIBILITY

**Current Support:**
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Uses Next.js 15 which requires:
  - ES2022 baseline
  - no IE11 support

**Missing:**
- No explicit browser version requirements
- No polyfill strategy documented
- No testing on older Safari versions (iOS 13)

**Recommendation:** Document minimum browser versions.

---

## 13. USER FLOW ANALYSIS

### Can Users Complete Key Workflows?

#### Registration → Dashboard
- ✗ BROKEN: After registration, not auto-logged in (see 2.1)
- ✓ Manual login works

#### Upload Document → Publish
- ✓ Can upload (with caveats on validation - see 2.2)
- ✓ Can view asset list with pagination
- ? Can't confirm: docs/architectures/publish flow not fully mapped

#### Search & QA
- ✓ Can search (with pagination issue - see 2.5)
- ✓ Can ask questions (QA mode)
- ✓ Can see related questions
- ✓ Can follow sources

#### Edit Document
- ✓ Can edit content
- ⚠ Unsaved changes warning works for page refresh only (see 2.4)
- ✓ Can save with change reason

#### User Management
- ✓ Can invite users
- ✓ Can view user list
- ? Can't confirm: no delete/edit UI visible

---

## SUMMARY TABLE

| Category | Count | Severity | Status |
|----------|-------|----------|--------|
| Critical Issues | 5 | P0 | 🔴 MUST FIX |
| High Priority | 5 | P1 | 🟠 MUST FIX |
| Moderate | 5 | P2 | 🟡 SHOULD FIX |
| Accessibility | 3 | P2 | 🟡 SHOULD FIX |
| Performance | 3 | P3 | 🔵 NICE TO FIX |
| Testing | 1 | P2 | 🟡 SHOULD FIX |
| **Total** | **22** | Mixed | Mixed |

---

## RECOMMENDATIONS & NEXT STEPS

### Immediate Actions (Before Public Beta)
1. **Fix syntax error** in forgot-password page (1.1)
2. **Remove token exposure** in password reset (1.2)
3. **Fix auth validation** in dashboard layout (1.3)
4. **Add CSRF protection** to API client (1.4)
5. **Sanitize QA output** (1.5)
6. **Fix registration flow** auto-login (2.1)
7. **Add file upload validation** (2.2)
8. **Replace toast global state** with Context (2.3)

### Before v1.0 Release
- Add accessibility fixes (4.1, 4.2, 4.3)
- Improve form UX (unsaved changes, validation)
- Add search pagination
- Test on mobile devices
- Add keyboard navigation
- Increase test coverage to >70%

### Post-Release Improvements
- Add export/download functionality
- Implement advanced search features
- Add real-time collaboration
- Analytics & monitoring
- Performance monitoring

---

## CONCLUSION

The KB Platform frontend demonstrates solid engineering fundamentals with a well-structured API abstraction layer, proper state management, and responsive design. However, **5 critical security/functionality issues must be resolved immediately** before any production deployment. The most severe is the hardcoded password reset token exposure and missing CSRF protection.

With fixes to the critical and high-priority items, the frontend will be **production-ready for beta testing**. Moderate issues should be addressed before v1.0.

**Recommended timeline:**
- **Week 1:** Fix critical issues (P0)
- **Week 2:** Fix high-priority issues (P1)
- **Week 3-4:** Address moderate issues (P2), increase test coverage
- **Week 5:** Internal testing, security review
- **Week 6:** Beta release

