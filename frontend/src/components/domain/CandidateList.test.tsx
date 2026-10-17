/**
 * The candidate list is where a manager decides who covers someone's work, so
 * these tests pin the two things that must never blur: an ineligible candidate
 * is not selectable, and a recommendation is not an assignment.
 */

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { CandidateList } from '@/components/domain/CandidateList'
import { candidate } from '@/test/factories'

const INELIGIBLE = candidate({
  user_id: 'eng-004',
  user_name: 'Mei Tanaka',
  eligible: false,
  total_score: 0,
  breakdown: [],
  ineligibility_reasons: ['No access authorisation for project(s): proj-payments'],
  summary: 'Mei Tanaka cannot be assigned.',
})

describe('CandidateList', () => {
  it('separates eligible candidates from candidates who cannot be assigned', () => {
    render(<CandidateList candidates={[candidate(), INELIGIBLE]} />)

    expect(screen.getByText('Eligible candidates (1)')).toBeInTheDocument()
    expect(screen.getByText('Not assignable (1)')).toBeInTheDocument()
  })

  it('states why an ineligible candidate cannot be assigned', () => {
    render(<CandidateList candidates={[candidate(), INELIGIBLE]} />)

    expect(
      screen.getByText('No access authorisation for project(s): proj-payments'),
    ).toBeInTheDocument()
  })

  it('offers no way to select an ineligible candidate', async () => {
    const onSelect = vi.fn()
    render(
      <CandidateList candidates={[candidate(), INELIGIBLE]} onSelect={onSelect} />,
    )

    // Exactly one Select button: the eligible candidate's.
    const selectButtons = screen.getAllByRole('button', { name: 'Select' })
    expect(selectButtons).toHaveLength(1)

    await userEvent.click(selectButtons[0])
    expect(onSelect).toHaveBeenCalledExactlyOnceWith('eng-001')
  })

  it('shows the scoring breakdown so a recommendation is explainable', () => {
    render(<CandidateList candidates={[candidate()]} />)

    // The top candidate's breakdown is expanded by default.
    expect(
      screen.getByText('Matches 3/3 required skill(s): backend, payments, python.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Assigned 36h of 40h weekly capacity (90% used).'),
    ).toBeInTheDocument()
    expect(screen.getByText('Relevant Skills')).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
  })

  it('marks the selected candidate without implying the assignment is made', () => {
    render(
      <CandidateList
        candidates={[candidate()]}
        selectedId="eng-001"
        onSelect={() => {}}
      />,
    )

    expect(screen.getByRole('button', { name: 'Selected' })).toBeInTheDocument()
    // Still described as eligible, not as assigned.
    expect(screen.getByText('Eligible')).toBeInTheDocument()
  })

  it('says plainly when no eligible candidate exists', () => {
    render(<CandidateList candidates={[INELIGIBLE]} />)

    expect(
      screen.getByText(/No eligible backup candidate was found/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Manual intervention is required/)).toBeInTheDocument()
  })

  it('ranks eligible candidates in the order given', () => {
    render(
      <CandidateList
        candidates={[
          candidate(),
          candidate({ user_id: 'eng-002', user_name: 'Lena Fischer', total_score: 72.5 }),
        ]}
      />,
    )

    const ranks = screen.getAllByText(/^Rank \d$/).map((node) => node.textContent)
    expect(ranks).toEqual(['Rank 1', 'Rank 2'])

    const first = screen.getByText('Arjun Mehta').closest('div')!
    expect(within(first).getByText('Rank 1')).toBeInTheDocument()
  })
})
