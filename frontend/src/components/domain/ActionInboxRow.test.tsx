/**
 * The inbox row is where a manager decides what to do next, so it has to carry
 * the consequence of not acting, not just the item's name.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { ActionInboxRow } from '@/components/domain/ActionInboxRow'
import { actionInboxItem } from '@/test/factories'

function renderRow(item = actionInboxItem(), onOpen?: (item: never) => void) {
  return render(
    <MemoryRouter>
      <ul>
        <ActionInboxRow item={item} onOpen={onOpen as never} />
      </ul>
    </MemoryRouter>,
  )
}

describe('ActionInboxRow', () => {
  it('states the downstream consequence of leaving the item', () => {
    renderRow()
    expect(
      screen.getByText(
        /Consequence: 2 dependent task\(s\) cannot proceed; 'Settlement API GA' is 3.0 day\(s\) away./,
      ),
    ).toBeInTheDocument()
  })

  it('shows the deterministic priority score and its group', () => {
    renderRow()
    expect(screen.getByText('92')).toBeInTheDocument()
    expect(screen.getByText('Urgent and time-sensitive')).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
  })

  it('reports an overdue action using the day count the server computed', () => {
    renderRow()
    expect(screen.getByText('1 day overdue')).toBeInTheDocument()
  })

  it('reports time remaining when the action is not yet due', () => {
    renderRow(
      actionInboxItem({
        priority_detail: { ...actionInboxItem().priority_detail, due_in_days: 3 },
      }),
    )
    expect(screen.getByText('3 days left')).toBeInTheDocument()
  })

  it('shows no due label when the action has no deadline', () => {
    renderRow(
      actionInboxItem({
        priority_detail: { ...actionInboxItem().priority_detail, due_in_days: null },
      }),
    )
    // The consequence text still mentions days, so assert on the due label's
    // own wording rather than on the word "day".
    expect(screen.queryByText(/overdue$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/left$/)).not.toBeInTheDocument()
    expect(screen.queryByText('Due today')).not.toBeInTheDocument()
  })

  it('names which tasks are blocked when expanded in the inbox', () => {
    renderRow()
    expect(screen.getByText(/Blocks 2 tasks: pay-02, pay-03/)).toBeInTheDocument()
  })

  it('opens the item when clicked', async () => {
    const onOpen = vi.fn()
    renderRow(actionInboxItem(), onOpen)
    await userEvent.click(screen.getByRole('button'))
    expect(onOpen).toHaveBeenCalledOnce()
  })
})
