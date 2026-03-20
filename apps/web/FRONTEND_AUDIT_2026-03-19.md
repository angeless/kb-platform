# Frontend Code Audit Report
**KB Platform Web Application**  
**Audit Date**: 2026-03-19  
**Framework**: Next.js 15.1.0 + React 19.0.0 + Tailwind CSS  

## Test Results Summary

**Test Run**: `npx vitest run`

- Total Tests: 10
- Passed: 7
- Failed: 3
- Test Files Passed: 3/4

### Failing Tests
- **File**: `src/__tests__/components/status-badge.test.tsx` (3 failures)
- **Issue**: "React is not defined" error in all 3 tests
- **Root Cause**: Missing React import in test file (JSX used without React import)
- **Severity**: HIGH - Tests are broken and blocking test suite

---

## 1. Authentication UX - CRITICAL ISSUES

### 1.1 Password Input Lacks Visibility Toggle
**Location**: 
- `/src/app/login/page.tsx` (lines 73-79)
- `/src/app/register/page.tsx` (lines 100-106, 113-119)

**Issue**: Password fields are always hidden (type="password") with no toggle button to show/hide password. Users cannot verify what they typed.

**Severity**: MEDIUM (UX friction)

**Fix Required**: Add show/hide password toggle icon for both password fields.

---

### 1.2 No "Forgot Password" Link
**Location**: `/src/app/login/page.tsx`

**Issue**: Login page completely lacks password reset functionality or "Forgot Password" link.

**Severity**: HIGH (User blocker - users cannot recover locked-out accounts)

**Fix Required**: Add "Forgot Password" link to initiate password recovery flow.

---

### 1.3 Email Validation Too Lenient
**Location**: `/src/app/login/page.tsx` (line 19)

**Issue**: Login only validates `email.trim()` - does not validate email format. User can enter "abc" and pass validation.

**Severity**: MEDIUM (Invalid data accepted)

**Fix Required**: Add proper email regex validation or use HTML5 email type validation.

---

### 1.4 Password Length Inconsistency
**Location**: 
- `/src/app/login/page.tsx` (line 23): Requires >= 8 characters
- `/src/app/register/page.tsx` (line 29): Requires >= 8 characters

**Issue**: While consistent between pages, the validation only checks length. No enforcement of uppercase/numbers during login, but register requires them. Login allows weaker passwords than registration expects.

**Severity**: MEDIUM (Asymmetric validation)

---

## 2. Token Management Security - CRITICAL ISSUES

### 2.1 JWT Stored in localStorage (XSS Vulnerability)
**Location**: `/src/stores/auth-store.ts` (line 39)

**Code**:
```typescript
localStorage.setItem("access_token", resp.data.access_token);
```

**Issue**: JWT token stored in localStorage. This is susceptible to XSS attacks. Any JavaScript code can steal the token.

**Severity**: CRITICAL (Security vulnerability)

**Recommended Fix**: Use httpOnly cookies instead of localStorage. This prevents JavaScript from accessing the token.

---

### 2.2 JWT Decoded Client-Side Without Verification
**Location**: `/src/stores/auth-store.ts` (lines 76-85)

**Code**:
```typescript
try {
  const payload = JSON.parse(atob(token.split(".")[1]));
  set({
    user: {
      id: payload.user_id,
      email: payload.email || "",
      role: payload.role || "",
      tenant_id: payload.tenant_id,
    },
  });
}
```

**Issue**: JWT is decoded client-side without signature verification. User role/permissions decoded from untrusted client-side data and used for rendering UI. Attacker can modify JWT payload in localStorage to escalate privileges on frontend.

**Severity**: CRITICAL (Authorization bypass risk)

**Recommendation**: Move role/permission checking to backend for critical operations. Use token only for API calls and trust backend for authorization.

---

### 2.3 No Token Refresh Logic
**Location**: `/src/lib/api.ts`

**Issue**: No token refresh mechanism. If JWT expires, user gets 401 error but cannot automatically refresh. No retry logic for expired tokens.

**Severity**: MEDIUM (Poor UX after token expiration)

**Required**: Implement token refresh endpoint call when API returns 401, then retry request. Or redirect to login on 401.

---

### 2.4 Token Expiration Not Checked Before API Calls
**Location**: `/src/lib/api.ts` (lines 20-23)

**Issue**: Token is retrieved from localStorage without checking expiration. If token is expired, API will reject it with 401.

**Severity**: MEDIUM (Silent failures)

**Recommendation**: Check JWT expiration client-side before making requests. Proactively redirect to login if token expired.

---

## 3. Dashboard Layout & Navigation - ISSUES

### 3.1 Sidebar Not Responsive/Mobile Unfriendly
**Location**: `/src/components/sidebar.tsx` (line 21)

**Code**:
```typescript
<aside className="flex h-screen w-56 flex-col border-r border-gray-200 bg-white">
```

**Issue**: Sidebar is fixed width `w-56` (224px) and takes up significant screen real estate on mobile. No mobile hamburger menu or collapsible sidebar. Layout will be unusable on phones (<375px).

**Severity**: MEDIUM (Mobile UX)

---

### 3.2 Role Information Display Lacks Context
**Location**: `/src/components/topbar.tsx` (lines 20-22)

**Code**:
```typescript
<span className="rounded bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700">
  {user?.role}
</span>
```

**Issue**: User's role is displayed as raw database value (e.g., "tenant_admin") instead of human-readable label. Compare with `/src/app/(dashboard)/settings/users/page.tsx` which maps roles to labels properly. Should display "租户管理员" not "tenant_admin".

**Severity**: LOW (Minor UX inconsistency)

---

## 4. Project Management - ISSUES

### 4.1 Create Project Form Has No Validation Messages
**Location**: `/src/app/(dashboard)/projects/page.tsx` (lines 63-90)

**Issue**: Form doesn't show inline validation errors as user types. Only shows general error after form submit. No field-level feedback.

**Severity**: LOW (Minor UX)

---

### 4.2 Project Status on Cards Not Localized
**Location**: `/src/app/(dashboard)/projects/page.tsx` (line 112)

**Issue**: Project status displays raw enum value (e.g., "active") without Chinese translation. Inconsistent with rest of app which uses StatusBadge for translation.

**Severity**: LOW (Localization inconsistency)

---

## 5. File Upload Component - ISSUES

### 5.1 No Upload Progress Indication
**Location**: `/src/components/file-upload.tsx` (lines 109-136)

**Issue**: Upload shows "上传中..." text status but no progress bar. For large files, user has no indication of progress. Cannot see upload speed or estimated time remaining.

**Severity**: MEDIUM (Large file UX)

---

### 5.2 No Retry Mechanism for Failed Uploads
**Location**: `/src/components/file-upload.tsx` (lines 36-46)

**Issue**: When upload fails, item status changes to "error" with message, but there's no "Retry" button. User must manually reload page and re-upload.

**Severity**: MEDIUM (UX friction)

---

### 5.3 Upload Cannot Be Cancelled Mid-Stream
**Location**: `/src/components/file-upload.tsx`

**Issue**: Once upload starts (line 21), there's no way to cancel. No AbortController used. For slow connections, user is stuck waiting.

**Severity**: MEDIUM (User control)

---

### 5.4 No File Size Validation Client-Side
**Location**: `/src/components/file-upload.tsx` (lines 49-64)

**Issue**: Component accepts any file size without validation. Large files will upload and timeout at server. No client-side size limit check before upload.

**Severity**: MEDIUM (Wasted bandwidth)

---

### 5.5 Type Guessing Incomplete
**Location**: `/src/components/file-upload.tsx` (lines 141-153)

**Issue**: The `guessType()` function doesn't recognize many file types. Returns "document" for unknown types. Should have more complete mapping or server-side type detection.

**Severity**: LOW (Minor typing)

---

## 6. Document Viewing/Editing - ISSUES

### 6.1 Markdown XSS Not Fully Safe
**Location**: `/src/components/markdown-view.tsx` (line 13)

**Code**:
```typescript
<ReactMarkdown>{content}</ReactMarkdown>
```

**Issue**: React-markdown library is used without explicit XSS plugins configured. While React-markdown is safer than `dangerouslySetInnerHTML`, it can still render HTML/JavaScript in some cases. No `skipHtml` prop set (defaults to false, allowing HTML).

**Severity**: MEDIUM (Potential XSS via markdown)

**Fix**: Add `skipHtml={true}` and `allowedElements` props to ReactMarkdown to restrict dangerous elements.

---

### 6.2 Version History Not Clearly Marked as Read-Only
**Location**: `/src/app/(dashboard)/docs/[id]/page.tsx` (lines 129-147)

**Issue**: When viewing old versions, UI doesn't clearly indicate this is read-only historical data. User might think they're editing when they're just viewing.

**Severity**: LOW (Minor UX clarity)

---

### 6.3 Edit Page Doesn't Prevent Concurrent Edits
**Location**: `/src/app/(dashboard)/docs/[id]/edit/page.tsx`

**Issue**: Multiple users can open same doc in edit mode simultaneously. No locking or conflict detection. Last save wins (data loss risk).

**Severity**: MEDIUM (Data loss risk)

---

### 6.4 No Unsaved Changes Warning
**Location**: `/src/app/(dashboard)/docs/[id]/edit/page.tsx`

**Issue**: If user has edited content and clicks browser back/refresh, no warning about unsaved changes.

**Severity**: MEDIUM (Data loss risk)

---

## 7. Search Page - ISSUES

### 7.1 Semantic Search Empty Message Assumes Missing Embeddings
**Location**: `/src/app/(dashboard)/projects/[id]/search/page.tsx` (line 183)

**Issue**: When semantic search returns 0 results, message is "没有找到语义相关的文档，请先为文档生成 embedding" - assumes embeddings are missing. Should check actual cause.

**Severity**: LOW (May be inaccurate message)

---

## 8. Architecture Tree Component - ISSUES

### 8.1 Tree Nodes Expanded by Default
**Location**: `/src/components/tree-node.tsx` (line 33)

**Issue**: All nodes are expanded by default (`useState(true)`). For large trees, this renders all children immediately, causing performance issues.

**Severity**: MEDIUM (Performance for large trees)

---

### 8.2 No Loading State While Rendering Large Trees
**Location**: Tree rendering pages

**Issue**: If architecture tree is very large, rendering is synchronous and can block main thread.

**Severity**: LOW (Depends on tree size)

---

## 9. Settings Pages - ISSUES

### 9.1 User Invite Has No Email Format Validation
**Location**: `/src/app/(dashboard)/settings/users/page.tsx` (line 75)

**Issue**: Email input uses `type="email"` but doesn't validate on blur/change. Can submit form with invalid email format.

**Severity**: LOW (HTML5 validation exists but no explicit feedback)

---

### 9.2 Role Selection Has No Help Text
**Location**: `/src/app/(dashboard)/settings/users/page.tsx` (lines 78-82)

**Issue**: Dropdown shows role options without descriptions. Users don't know what each role can do.

**Severity**: MEDIUM (UX clarity)

---

### 9.3 API Key Visibility Not Configurable
**Location**: `/src/app/(dashboard)/settings/models/page.tsx` (line 116)

**Issue**: API key field is always `type="password"`. No show/hide toggle. Also, form submits with plaintext key in request body (should be encrypted or sent over HTTPS only - which it is, but form shows no security indication).

**Severity**: MEDIUM (UX - user can't verify key is correct)

---

### 9.4 Audit Log Details Truncated
**Location**: `/src/app/(dashboard)/settings/audit/page.tsx` (line 120)

**Issue**: Audit log detail JSON is truncated to 50 characters with `.slice(0, 50)`. Full details are not accessible.

**Severity**: LOW (Limited audit visibility)

---

## 10. General Code Quality Issues

### 10.1 Unused Dependency: lucide-react
**Location**: `package.json` (line 18)

**Issue**: `lucide-react` is installed but never imported anywhere. The app uses emoji icons instead.

**Severity**: LOW (Unused dependency, increases bundle)

**Fix**: Remove from dependencies or use it for consistent icon library.

---

### 10.2 Missing useCallback Dependency in Dashboard Layout
**Location**: `/src/app/(dashboard)/layout.tsx` (line 19)

**Code**:
```typescript
useEffect(() => {
  checkAuth();
}, [checkAuth]);
```

**Issue**: `checkAuth` is included in dependency array, but `checkAuth` is a function reference from zustand store. This might cause infinite loops if zustand doesn't memoize. However, zustand should handle this - needs testing.

**Severity**: LOW-MEDIUM (Potential infinite loop risk)

---

### 10.3 Inconsistent Error Message Formatting
**Multiple locations**: Error messages are displayed but don't distinguish between different error types (network, validation, authorization, server error).

**Severity**: LOW (UX clarity)

---

### 10.4 Missing Loading Skeletons
**Issue**: All pages show generic "加载中..." text while loading. No skeleton screens or progressive loading indication.

**Severity**: LOW (Poor perceived performance)

---

### 10.5 No Error Boundaries
**Location**: No error boundary components in app

**Issue**: If any component throws an error, entire page crashes with white screen. No graceful error UI.

**Severity**: MEDIUM (Poor error UX)

---

## 11. Test Suite Issues

### 11.1 Test File Missing React Import
**Location**: `/src/__tests__/components/status-badge.test.tsx`

**Code**:
```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/status-badge";
```

**Issue**: File uses JSX in `render(<StatusBadge />)` but doesn't import React. Modern React doesn't require this in .tsx files, but vitest setup might require it.

**Severity**: MEDIUM (3 tests currently fail)

**Fix**: Add `import React from "react";` or update vitest config to handle JSX automatically.

---

## Summary by Severity

| Severity | Count | Categories |
|----------|-------|-----------|
| CRITICAL | 2 | Token security (localStorage), JWT verification |
| HIGH | 2 | No forgot password, missing password toggle |
| MEDIUM | 15 | Upload UX, doc concurrency, mobile, markdown XSS, test failures |
| LOW | 8 | Localization, role labels, audit truncation |

---

## Recommended Priorities

### Immediate (Before Production Release)
1. **Fix test failures** - Add React import to status-badge.test.tsx
2. **Implement password visibility toggle** - Core UX feature
3. **Add "Forgot Password"** - Critical user recovery path
4. **Secure token storage** - Use httpOnly cookies instead of localStorage
5. **Verify JWT client-side** - Don't trust client-side role information for security decisions

### Soon (Next Sprint)
6. Token refresh logic implementation
7. Add markdown XSS protection
8. Implement unsaved changes warning
9. Add error boundaries
10. Improve mobile responsiveness

### Nice-to-Have
11. Upload progress bars
12. Upload retry mechanism
13. Semantic search empty state messaging
14. Audit log full detail viewing
15. Remove unused lucide-react dependency

