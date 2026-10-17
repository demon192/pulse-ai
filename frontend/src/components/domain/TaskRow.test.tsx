/**
 * A task row must show the dependency and blocker context a manager reads
 * first — and must not editorialise about the person who owns it.
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { TaskRow } from '@/components/domain/TaskRow'
import { taskView } from '@/test/factories'

function renderRow(view = taskView(), showProject = false) {
  return render(
    <MemoryRouter>
      <ul>
        <TaskRow view={view} showProject={showProject} />
      </ul>
    </MemoryRouter>,
  )
}

describe('TaskRow', () => {
  it('shows the recorded status, priority and owner', () => {
    renderRow()
    expect(screen.getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
    expect(screen.getByText(/Rhea Kapoor/)).toBeInTheDocument()
  })

  it('shows the recorded blocker reason rather than a guess', () => {
    renderRow()
    expect(
      screen.getByText('Blocker: Partial-refund field semantics are still undecided.'),
    ).toBeInTheDocument()
  })

  it('names the dependency the task is waiting on', () => {
    renderRow()
    expect(
      screen.getByText('Waiting on: Define settlement API contract'),
    ).toBeInTheDocument()
  })

  it('reports how much work depends on it', () => {
    renderRow()
    expect(screen.getByText('1 task depend on this')).toBeInTheDocument()
  })

  it('shows the next step so a reader knows what happens next', () => {
    renderRow()
    expect(
      screen.getByText('Next step: Resume once contract v3 is approved.'),
    ).toBeInTheDocument()
  })

  it('marks an overdue task without attributing it to its owner', () => {
    renderRow(taskView({ is_overdue: true, days_until_due: -2 }))
    expect(screen.getByText('Overdue')).toBeInTheDocument()
    expect(screen.getByText(/2 days overdue/)).toBeInTheDocument()
    // Nothing characterises the person.
    expect(screen.queryByText(/behind|slow|underperform/i)).not.toBeInTheDocument()
  })

  it('says plainly when a task has no due date', () => {
    renderRow(
      taskView({
        task: { ...taskView().task, due_date: null },
        days_until_due: null,
      }),
    )
    expect(screen.getByText(/No due date/)).toBeInTheDocument()
  })
})
