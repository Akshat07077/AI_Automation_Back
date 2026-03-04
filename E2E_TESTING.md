# End-to-End Testing Guide

This document outlines the critical user flows that should be tested before and after deployment.

## Pre-Deployment Testing Checklist

### 1. Authentication Flow

#### Admin Login
- [ ] Navigate to `/login`
- [ ] Leave username blank or enter "admin"
- [ ] Enter admin password
- [ ] Verify redirect to dashboard
- [ ] Verify dashboard loads correctly

#### User Registration (Admin Only)
- [ ] Login as admin
- [ ] Navigate to `/register`
- [ ] Enter new username (min 3 chars)
- [ ] Enter new password (min 6 chars)
- [ ] Verify user is created successfully
- [ ] Verify user appears in users list

#### Registered User Login
- [ ] Logout from admin account
- [ ] Navigate to `/login`
- [ ] Enter registered username
- [ ] Enter registered password
- [ ] Verify login succeeds
- [ ] Verify dashboard access

#### Logout
- [ ] Click "Logout" button in header
- [ ] Verify redirect to login page
- [ ] Verify cannot access dashboard without login

### 2. Lead Management

#### Import Leads
- [ ] Login as admin/user
- [ ] Navigate to dashboard
- [ ] Click "Import Leads" button
- [ ] Verify leads are imported from Google Sheet
- [ ] Verify success message shows count
- [ ] Verify leads appear in "Recent Leads" table
- [ ] Verify leads summary updates

#### View Leads
- [ ] Verify "Recent Leads" table displays correctly
- [ ] Verify lead information (founder, startup, email, status)
- [ ] Verify status badges display correctly
- [ ] Verify pagination works (if >10 leads)

#### Filter Leads by Status
- [ ] Filter by "New" status
- [ ] Filter by "Sent" status
- [ ] Filter by "Replied" status
- [ ] Filter by "Bounce" status
- [ ] Verify correct leads are shown

### 3. Outreach Operations

#### Run Outreach Batch
- [ ] Ensure there are "New" leads in the system
- [ ] Click "Run Outreach Batch" button
- [ ] Verify success message
- [ ] Wait a few seconds
- [ ] Verify leads status changes to "Sent"
- [ ] Verify "Emails Sent Today" counter updates
- [ ] Verify outreach logs appear in "Sent Emails & Activity" table

#### View Outreach Logs
- [ ] Navigate to "Sent Emails & Activity" section
- [ ] Verify logs display correctly
- [ ] Verify event types (sent, replied, bounce, follow_up)
- [ ] Verify filters work (All, Sent, Replies, Bounces, Follow-Ups)
- [ ] Verify "Resend" button appears for sent emails

#### Resend Email
- [ ] Click "Resend" button on a lead
- [ ] Verify success message
- [ ] Verify new log entry is created
- [ ] Verify lead status remains "Sent"

### 4. Follow-Ups

#### View Follow-Ups
- [ ] Navigate to `/follow-ups`
- [ ] Verify page loads correctly
- [ ] Verify leads with follow-ups are displayed
- [ ] Verify status badges (Due Now, Scheduled, No Follow-up)
- [ ] Verify follow-up count displays correctly

#### Send Follow-Up
- [ ] Find a lead with "Due Now" status
- [ ] Click "Send" button
- [ ] Verify success message
- [ ] Verify follow-up count increments
- [ ] Verify lead moves to next scheduled date

#### Process All Due Follow-Ups
- [ ] Ensure there are due follow-ups
- [ ] Click "Process All Due" button
- [ ] Verify success message
- [ ] Verify all due follow-ups are sent
- [ ] Verify follow-up counts update

### 5. Activity Log

#### View Activity Log
- [ ] Navigate to `/activity`
- [ ] Verify page loads correctly
- [ ] Verify activity entries display
- [ ] Verify activity types (email_sent, email_replied, email_bounced, follow_up_sent)
- [ ] Verify timestamps display correctly
- [ ] Verify activity icons display correctly

#### Filter Activity
- [ ] Filter by "All Events"
- [ ] Filter by "Emails Sent"
- [ ] Filter by "Follow-Ups"
- [ ] Filter by "Replies"
- [ ] Filter by "Bounces"
- [ ] Verify correct activities are shown

#### Activity Summary
- [ ] Verify summary cards display (Emails Sent, Follow-Ups, Replies, Bounces)
- [ ] Verify "Last 7 days" data is correct

### 6. Statistics & Dashboard

#### View Statistics
- [ ] Verify "Emails Sent Today" counter
- [ ] Verify "Replies Today" counter
- [ ] Verify "Bounces Today" counter
- [ ] Verify "Reply Rate" percentage
- [ ] Verify statistics update after operations

#### View Leads Summary
- [ ] Verify "Leads by Status" section
- [ ] Verify counts for New, Sent, Replied, Bounce
- [ ] Verify counts match actual lead counts

#### View Conversion Rate
- [ ] Verify conversion rate displays correctly
- [ ] Verify calculation: (replies / sent) * 100

### 7. Error Handling

#### Invalid Login
- [ ] Try login with wrong password
- [ ] Verify error message displays
- [ ] Verify no redirect occurs

#### Network Errors
- [ ] Disconnect backend
- [ ] Try to import leads
- [ ] Verify error message displays
- [ ] Verify error notification appears

#### Invalid Data
- [ ] Try to register user with short username (<3 chars)
- [ ] Verify validation error
- [ ] Try to register user with short password (<6 chars)
- [ ] Verify validation error

## Post-Deployment Testing

### Production Environment

#### Verify Environment Variables
- [ ] Backend: All required env vars are set
- [ ] Frontend: `NEXT_PUBLIC_API_BASE_URL` points to production
- [ ] Frontend: `ADMIN_PASSWORD` is set
- [ ] Verify no localhost URLs in production

#### Verify CORS
- [ ] Frontend can make requests to backend
- [ ] No CORS errors in browser console
- [ ] All API calls succeed

#### Verify Database
- [ ] Database connection works
- [ ] Tables are created correctly
- [ ] Migrations ran successfully
- [ ] Users table exists

#### Verify External Services
- [ ] Google Sheets API works
- [ ] Gemini API works
- [ ] SMTP email sending works
- [ ] IMAP email monitoring works (if enabled)
- [ ] Telegram notifications work (if enabled)

### Performance Testing

#### Load Testing
- [ ] Test with 100+ leads
- [ ] Verify import performance
- [ ] Verify dashboard load time
- [ ] Verify API response times

#### Background Jobs
- [ ] Verify IMAP polling runs
- [ ] Verify follow-up processing runs
- [ ] Verify no errors in background jobs

## Automated Testing (Future)

### Unit Tests
- [ ] Password hashing/verification
- [ ] User creation/validation
- [ ] Lead import logic
- [ ] Email generation

### Integration Tests
- [ ] API endpoint tests
- [ ] Database operations
- [ ] External API calls (mocked)

### E2E Tests (Playwright/Cypress)
- [ ] Login flow
- [ ] Lead import
- [ ] Outreach batch
- [ ] Follow-up sending

## Test Data

### Sample Leads (for testing)
Create a test Google Sheet with:
- Founder Name
- Startup Name
- Email (valid format)
- Hiring Role (optional)
- Website (optional)
- Observation (optional)

### Test Accounts
- Admin account: Use `ADMIN_PASSWORD`
- Test user: Register via `/register` page

## Common Issues & Solutions

### Issue: Import leads returns 500 error
- **Check**: Google Sheets ID is correct
- **Check**: Service account file is accessible
- **Check**: Sheet is shared with service account
- **Check**: Google Sheets API is enabled

### Issue: CORS errors
- **Check**: Frontend URL is in `ALLOWED_ORIGINS`
- **Check**: `NEXT_PUBLIC_API_BASE_URL` is correct
- **Check**: Backend CORS middleware is configured

### Issue: Login fails
- **Check**: `ADMIN_PASSWORD` is set correctly
- **Check**: User exists in database (if registered user)
- **Check**: Backend API is accessible

### Issue: Emails not sending
- **Check**: SMTP credentials are correct
- **Check**: App Password is used (for Gmail)
- **Check**: Firewall/network restrictions
- **Check**: Email limits not exceeded

---

**Last Updated**: [Current Date]
**Tested By**: [Tester Name]
**Status**: Pre-Production
