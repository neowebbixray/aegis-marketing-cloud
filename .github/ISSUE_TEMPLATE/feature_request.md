---
name: Feature Request
description: Suggest an idea or enhancement for Aegis Marketing Cloud
title: "[Feature] "
labels: ["enhancement", "triage"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        Thanks for helping improve Aegis Marketing Cloud! Please describe your idea clearly.

  - type: input
    id: summary
    attributes:
      label: Feature Summary
      description: A clear, concise description of the feature or enhancement
      placeholder: "e.g. Add A/B testing for email campaign variants"
    validations:
      required: true

  - type: dropdown
    id: area
    attributes:
      label: Affected Area
      description: Which area would this feature affect?
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
        - Marketplace / Plugins
        - Deployment / Infrastructure
        - Documentation
        - Developer Experience (DX)
    validations:
      required: true

  - type: textarea
    id: problem
    attributes:
      label: Problem Statement
      description: What problem does this feature solve? Describe the pain point or limitation.
      placeholder: "Currently it's difficult to... This is a problem because..."
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
      description: Describe the solution you'd like. Be specific about how it should work.
      placeholder: "I'd like to see a new capability that..."
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
      description: What alternative solutions or workarounds have you considered?
      placeholder: "An alternative would be... but the proposed solution is better because..."
    validations:
      required: false

  - type: textarea
    id: context
    attributes:
      label: Additional Context
      description: |
        Add any other context, mockups, diagrams, or references that help explain the feature.
        You can attach images or files by clicking this area and dragging them in.
      placeholder: "Add any reference links, screenshots, or relevant context here..."
    validations:
      required: false

  - type: checkboxes
    id: impact
    attributes:
      label: Impact Assessment
      options:
        - label: This feature would benefit most users of Aegis Marketing Cloud
        - label: I am willing to contribute to the implementation of this feature
        - label: This feature requires changes to the API or database schema
        - label: This feature has implications for security or data privacy

  - type: checkboxes
    id: checks
    attributes:
      label: Pre-submission Checklist
      options:
        - label: I have searched existing issues and this is not a duplicate
          required: true
        - label: I have described a clear problem and proposed solution
          required: true
