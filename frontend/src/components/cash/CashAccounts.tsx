import { Landmark, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { useDeleteCashAccount, useSaveCashAccount, type CashAccount } from '@/api/queries'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText, Field } from '@/components/Field'
import { RowActions } from '@/components/RowActions'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { useConfirm } from '@/hooks/use-confirm'
import { inr } from '@/lib/money'
import { formatDateTime } from '@/lib/time'

import { PURPOSE_INFO, PURPOSE_LABELS, type Purpose } from './labels'

/** Cash accounts: current balances, each with a purpose. Add and edit in a dialog. */
export function CashAccounts({ accounts }: { accounts: CashAccount[] }) {
  const [editing, setEditing] = useState<CashAccount | 'new' | null>(null)
  const remove = useDeleteCashAccount()
  const confirm = useConfirm()

  async function onDelete(account: CashAccount) {
    if (!(await confirm({ title: `Delete ${account.name}?` }))) return
    remove.mutate(account.id, { onSuccess: () => toast.success(`${account.name} deleted`) })
  }

  const add = (
    <Button variant="outline" onClick={() => setEditing('new')}>
      <Plus /> Add account
    </Button>
  )

  return (
    <section className="flex flex-col gap-3">
      {accounts.length === 0 ? (
        <EmptyState icon={Landmark} title="No cash accounts" action={add} />
      ) : (
        <>
          <Table label="Cash accounts">
            <THead>
              <Th>Account</Th>
              <Th>Purpose</Th>
              <Th numeric>Balance</Th>
              <Th numeric>Updated</Th>
              <Th />
            </THead>
            <TBody>
              {accounts.map((account) => (
                <Tr key={account.id}>
                  <Td>
                    <div className="font-medium">{account.name}</div>
                    {account.note && (
                      <div className="text-muted-foreground text-xs">{account.note}</div>
                    )}
                  </Td>
                  <Td>
                    <Badge variant={account.earmark === 'deployable' ? 'default' : 'secondary'}>
                      {PURPOSE_LABELS[account.earmark]}
                    </Badge>
                  </Td>
                  <Td numeric>{inr(account.balance)}</Td>
                  <Td numeric className="text-muted-foreground text-xs">
                    {formatDateTime(account.updated_at)}
                  </Td>
                  <Td className="w-0">
                    <RowActions
                      label={`Actions for ${account.name}`}
                      actions={[
                        { label: 'Edit', icon: Pencil, onSelect: () => setEditing(account) },
                        {
                          label: 'Delete',
                          icon: Trash2,
                          destructive: true,
                          onSelect: () => void onDelete(account),
                        },
                      ]}
                    />
                  </Td>
                </Tr>
              ))}
            </TBody>
          </Table>
          <div>{add}</div>
        </>
      )}
      <ErrorText error={remove.error} />
      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        {editing && (
          <AccountDialog
            key={editing === 'new' ? 'new' : editing.id}
            account={editing === 'new' ? undefined : editing}
            onDone={() => setEditing(null)}
          />
        )}
      </Dialog>
    </section>
  )
}

function AccountDialog({ account, onDone }: { account?: CashAccount; onDone: () => void }) {
  const save = useSaveCashAccount()
  const [draft, setDraft] = useState({
    name: account?.name ?? '',
    balance: account?.balance ?? '',
    earmark: account?.earmark ?? ('deployable' as Purpose),
    note: account?.note ?? '',
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate(
      {
        id: account?.id,
        body: { ...draft, balance: draft.balance.trim(), note: draft.note || null },
      },
      {
        onSuccess: () => {
          toast.success(account ? `${draft.name} saved` : `${draft.name} added`)
          onDone()
        },
      },
    )
  }

  const title = account ? `Edit ${account.name}` : 'Add account'
  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription className="sr-only">Name, balance and purpose</DialogDescription>
      </DialogHeader>
      <form aria-label={title} className="flex flex-col gap-4" onSubmit={submit}>
        <Field label="Name">
          {(id) => (
            <Input
              id={id}
              required
              value={draft.name}
              placeholder="Savings account"
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          )}
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Balance (₹)">
            {(id) => (
              <Input
                id={id}
                inputMode="decimal"
                required
                placeholder="1,00,000"
                value={draft.balance}
                onChange={(event) => setDraft({ ...draft, balance: event.target.value })}
              />
            )}
          </Field>
          <Field
            label="Purpose"
            info={
              <>
                Investable: {PURPOSE_INFO.deployable} Reserved: {PURPOSE_INFO.reserved} Emergency:{' '}
                {PURPOSE_INFO.emergency}
              </>
            }
          >
            {(id) => (
              <NativeSelect
                id={id}
                value={draft.earmark}
                onChange={(event) => setDraft({ ...draft, earmark: event.target.value as Purpose })}
              >
                {(Object.keys(PURPOSE_LABELS) as Purpose[]).map((value) => (
                  <option key={value} value={value}>
                    {PURPOSE_LABELS[value]}
                  </option>
                ))}
              </NativeSelect>
            )}
          </Field>
        </div>
        <Field label="Note">
          {(id) => (
            <Input
              id={id}
              value={draft.note}
              onChange={(event) => setDraft({ ...draft, note: event.target.value })}
            />
          )}
        </Field>
        <ErrorText error={save.error} />
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onDone}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {account ? 'Save' : 'Add account'}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  )
}
