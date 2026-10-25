import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ConfirmProvider } from '@/components/ConfirmProvider'
import { InfoTip } from '@/components/InfoTip'
import { useConfirm } from '@/hooks/use-confirm'

test('an info tip opens on focus and on tap', async () => {
  render(<InfoTip label="XIRR">Annual return on your cash flows.</InfoTip>)
  const button = screen.getByRole('button', { name: 'About XIRR' })
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

  await userEvent.tab()
  expect(button).toHaveFocus()
  expect(await screen.findByRole('tooltip')).toHaveTextContent('Annual return on your cash flows.')

  await userEvent.keyboard('{Escape}')
  await userEvent.click(button)
  expect(await screen.findByRole('tooltip')).toBeInTheDocument()
})

function DeleteButton({ onAnswer }: { onAnswer: (yes: boolean) => void }) {
  const confirm = useConfirm()
  return (
    <button onClick={async () => onAnswer(await confirm({ title: 'Delete Savings?' }))}>
      Delete
    </button>
  )
}

test('the confirm dialog answers yes or no', async () => {
  const onAnswer = vi.fn()
  render(
    <ConfirmProvider>
      <DeleteButton onAnswer={onAnswer} />
    </ConfirmProvider>,
  )

  await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
  expect(screen.getByRole('alertdialog', { name: 'Delete Savings?' })).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(onAnswer).toHaveBeenLastCalledWith(false)

  await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
  await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
  expect(onAnswer).toHaveBeenLastCalledWith(true)
})
