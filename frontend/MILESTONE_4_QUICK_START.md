# Milestone 4 Quick Start Guide

Get the DisruptIQ frontend running in 5 minutes.

## Prerequisites

- Node.js 20+ installed
- pnpm installed globally
- Backend running on `http://localhost:8000`

## Installation

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies (first time only)
pnpm install

# 3. Start development server
pnpm dev
```

Frontend runs on `http://localhost:3000`.

## Login

Visit `http://localhost:3000` and login with:

**Manager (full access):**
- Username: `manager_01`
- Password: `password`

**Analyst (read-only):**
- Username: `analyst_01`
- Password: `password`

## Quick Test Flow

### 1. View Dashboard
- See 4 KPI cards with metrics
- View SLA Risk chart
- Review recent disruptions

### 2. Create Test Disruption
1. Click "Disruptions" in sidebar
2. Click "Create Test Disruption"
3. Fill form:
   - Type: `late_truck`
   - Severity: `4`
   - Details: `{"truck_id": "T-123", "delay_hours": 6}`
4. Click "Create"

### 3. Run Pipeline
1. Click "Run Pipeline" in navbar (or go to "Run Planner" page)
2. Select the disruption you just created
3. Click "Run Pipeline"
4. Watch stepper update in real-time (~30-60s)
5. Click "View Scenarios" when done

### 4. Review Scenarios
1. Expand disruption group
2. Review scenario cards
3. Note "Recommended" badge on best option
4. Click "View Full Plan" to see details

### 5. Approve Scenario (Manager Only)
1. Click "Approve" on a scenario
2. Enter optional note
3. Submit
4. See toast notification (success or constraint error)

### 6. Check Approval Queue
1. Click "Approvals" in sidebar (manager only)
2. Review scenarios needing approval
3. Use bulk approve or individual actions

### 7. View Audit Log
1. Click "Audit Log" in sidebar
2. Filter by agent, decision, dates
3. Expand rows to see full details
4. Click "Export" to download JSON

## Common Commands

```bash
# Development
pnpm dev          # Start dev server

# Production
pnpm build        # Build for production
pnpm start        # Start production server

# Linting
pnpm lint         # Run ESLint
```

## Environment Variables (Optional)

Create `.env.local` to override API URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Default is `http://localhost:8000` (no config needed for local dev).

## Troubleshooting

### "Cannot connect to API"
```bash
# Ensure backend is running
cd ../backend
./run_milestone3.sh
# Or: uvicorn app.main:app --reload
```

### "401 Unauthorized"
- Token expired (24h default)
- Log out and back in
- Check backend JWT_SECRET hasn't changed

### "Module not found"
```bash
# Reinstall dependencies
rm -rf node_modules .next
pnpm install
```

### Styles not applying
```bash
# Clear Next.js cache
rm -rf .next
pnpm dev
```

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Pages (Next.js App Router)
│   ├── components/       # UI components
│   ├── lib/              # API client, types, auth
│   └── hooks/            # Data fetching hooks
├── public/               # Static assets
├── package.json          # Dependencies
└── tailwind.config.ts    # Tailwind config
```

## Key Features

- **JWT Auth:** Login with username/password
- **Role-Based Access:** Manager vs Analyst permissions
- **Real-Time Updates:** SWR auto-refresh (10-15s intervals)
- **Pipeline Polling:** 2s updates while running
- **Glassmorphism Theme:** Dark gradient background + frosted glass cards
- **Skeleton Loaders:** No spinners, glass shimmer animation
- **Toast Notifications:** All user actions have feedback
- **Error Handling:** 401 auto-logout, constraint violations, network errors

## Next Steps

1. **Explore Pages:** Dashboard, Disruptions, Scenarios, Approvals, Audit, Run
2. **Test Roles:** Login as analyst to see read-only restrictions
3. **Review Code:** Check `src/lib/types.ts` for all interfaces
4. **Customize Theme:** Edit `src/app/globals.css` for colors/styles
5. **Add Features:** See `MILESTONE_4_README.md` for enhancement ideas

## Documentation

- **Full README:** `MILESTONE_4_README.md`
- **Completion Report:** `../MILESTONE_4_COMPLETE.md`
- **Backend API:** `../backend/MILESTONE_3_README.md`
- **Project Overview:** `../README.md`

## Support

For issues or questions:
1. Check `MILESTONE_4_README.md` troubleshooting section
2. Review browser console for errors
3. Check backend logs for API errors
4. Verify environment variables are correct

---

**Status:** ✅ Ready to Use  
**Version:** Next.js 16.1.6  
**Last Updated:** March 2026
