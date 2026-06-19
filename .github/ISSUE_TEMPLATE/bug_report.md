---
name: Bug Report
description: Report a reproducible bug or unexpected behavior
title: "[Bug] "
labels: ["bug", "triage"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report! Please provide as much detail as possible.

  - type: input
    id: summary
    attributes:
      label: Bug Summary
      description: A clear, concise description of the bug
      placeholder: "e.g. Campaign dashboard crashes when loading large datasets"
    validations:
      required: true

  - type: dropdown
    id: area
    attributes:
      label: Affected Area
      description: Which part of the system is affected?
      multiple: true
      options:
        - Backend API
        - Frontend UI
        - GraphQL
        - Data Pipeline / Workflow
        - AI / LLM Integration
        - Authentication / Authorization
        - Media Library
        - Reporting / Analytics
        - Deployment / Infrastructure
        - Documentation
    validations:
      required: true

  - type: textarea
    id: steps
    attributes:
      label: Steps to Reproduce
      description: Provide a minimal, clear set of steps to reproduce the issue
      placeholder: |
        1. Go to '...'
        2. Click on '...'
        3. Scroll down to '...'
        4. See error
      value: |
        1.
        2.
        3.
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior
      description: What did you expect to happen?
      placeholder: "The system should..."
    validations:
      required: true

  - type: textarea
    id: actual
    attributes:
      label: Actual Behavior
      description: What actually happened? Include error messages, stack traces, or screenshots if applicable.
      placeholder: "Instead, I saw..."
    validations:
      required: true

  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: Please fill in your environment details
      placeholder: |
        - Aegis MC Version: [e.g. 0.1.0]
        - Browser: [e.g. Chrome 120]
        - OS: [e.g. macOS 14.2, Ubuntu 22.04]
        - Deployment: [e.g. Docker, local dev, production]
        - Database: [e.g. PostgreSQL 16]
    validations:
      required: false

  - type: textarea
    id: logs
    attributes:
      label: Relevant Logs / Screenshots
      description: Copy and paste any relevant log output or attach screenshots. This will be automatically formatted.
      render: shell
    validations:
      required: false

  - type: checkboxes
    id: checks
    attributes:
      label: Pre-submission Checklist
      options:
        - label: I have searched existing issues and this is not a duplicate
          required: true
        - label: I have provided clear, reproducible steps
          required: true
        - label: I have removed any sensitive/confidential information
          required: true
