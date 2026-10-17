/**
 * A brief that silently omits a section, or hides what it could not find out,
 * is worse than no brief. These tests pin both.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HandoverBriefView } from '@/components/domain/HandoverBriefView'
import { handoverBrief } from '@/test/factories'

const REQUIRED_HEADINGS = [
  'Task and project objective',
  'Current status',
  'Work completed',
  'Relevant files, links and documents',
  'Decisions already made',
  'Unresolved questions',
  'Dependencies and affected tasks',
  'Known blockers',
  'Suggested next steps',
  'Relevant contacts and reviewers',
  'Missing information to confirm',
]

describe('HandoverBriefView', () => {
  it('renders all eleven required sections', () => {
    render(<HandoverBriefView brief={handoverBrief()} />)

    for (const heading of REQUIRED_HEADINGS) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
    }
  })

  it('labels how each section was derived', () => {
    render(<HandoverBriefView brief={handoverBrief()} />)

    expect(screen.getAllByText('Verified fact')).toHaveLength(10)
    expect(screen.getByText('Recommendation')).toBeInTheDocument()
  })

  it('shows missing information as prominently as the content', () => {
    render(
      <HandoverBriefView
        brief={handoverBrief()}
        missingInformation={[
          'No next step is recorded.',
          'The engineer did not write handover notes.',
        ]}
      />,
    )

    expect(
      screen.getByText('Missing information to confirm with a human'),
    ).toBeInTheDocument()
    expect(screen.getByText('No next step is recorded.')).toBeInTheDocument()
    expect(
      screen.getByText('The engineer did not write handover notes.'),
    ).toBeInTheDocument()
  })

  it('says when a brief was assembled without the model', () => {
    render(<HandoverBriefView brief={handoverBrief()} />)
    expect(screen.getByText('Assembled from records')).toBeInTheDocument()
  })

  it('says when the model synthesised it', () => {
    render(<HandoverBriefView brief={handoverBrief({ generated_by: 'gemini' })} />)
    expect(screen.getByText('Synthesised by Gemini')).toBeInTheDocument()
  })

  it('cites the records behind each section', () => {
    render(<HandoverBriefView brief={handoverBrief()} />)
    expect(screen.getAllByText('Sources: pay-02').length).toBe(11)
  })
})
