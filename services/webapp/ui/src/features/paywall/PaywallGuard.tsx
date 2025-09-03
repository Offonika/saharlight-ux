import React from 'react'
import { Navigate } from 'react-router-dom'
import MedicalButton from '@/components/MedicalButton'

export type PaywallMode = 'off' | 'soft' | 'hard'
export type UserStatus = 'free' | 'pro'

interface PaywallGuardProps {
  children: React.ReactNode
  status?: UserStatus
  mode?: PaywallMode
}

const PaywallGuard: React.FC<PaywallGuardProps> = ({
  children,
  status,
  mode,
}) => {
  const paywallMode =
    mode ?? ((import.meta.env.VITE_PAYWALL_MODE as PaywallMode) || 'off')
  const userStatus =
    status ?? ((import.meta.env.VITE_USER_STATUS as UserStatus) || 'free')

  if (userStatus === 'pro' || paywallMode === 'off') {
    return <>{children}</>
  }

  console.log('[metrics] encountered paywall')

  if (paywallMode === 'soft') {
    return (
      <div className="p-4 text-center" data-testid="paywall-teaser">
        <p className="mb-2">Функция доступна в PRO-версии</p>
        <MedicalButton onClick={() => (window.location.href = '/subscription')}>
          Включить trial
        </MedicalButton>
      </div>
    )
  }

  return <Navigate to="/subscription" replace />
}

export default PaywallGuard

export const withPaywall = <P extends object>(
  Component: React.ComponentType<P>,
  mode?: PaywallMode,
  status?: UserStatus,
) => {
  return (props: P) => (
    <PaywallGuard mode={mode} status={status}>
      <Component {...props} />
    </PaywallGuard>
  )
}
