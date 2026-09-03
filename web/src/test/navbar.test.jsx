import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import NavBar from '../components/NavBar'

/*
  و-٩أ — اختبار معزول لا عبر `App.jsx`: يثبت أن استخراج `NavBar` من
  `PilotDeck.jsx` لم يغيّر السلوك، بمعزل عن بقية الشاشة.
*/

describe('NavBar — و-٩أ', () => {
  it('طيّار (isAdmin=false) يرى زرَّين فقط', () => {
    render(<NavBar isAdmin={false} onNavigate={() => {}} />)
    expect(screen.getByRole('button', { name: 'قراءاتي' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'محطة التزوّد' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'الأوزان' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(2)
  })

  it('مشرف (isAdmin=true) يرى الأزرار العشرة كلّها', () => {
    render(<NavBar isAdmin={true} onNavigate={() => {}} />)
    expect(screen.getAllByRole('button')).toHaveLength(10)
    for (const label of [
      'قراءاتي', 'محطة التزوّد', 'طابور القراءات', 'التقرير الدوري',
      'الأوزان', 'العتبات', 'الأسراب', 'سجلّ التغييرات',
      'أنشطة الوقود', 'تقييم نشاط',
    ]) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
  })

  it('النقر يمرّر مفتاح الشاشة الصحيح — لا تسمية العرض', async () => {
    const onNavigate = vi.fn()
    render(<NavBar isAdmin={true} onNavigate={onNavigate} />)
    await userEvent.click(screen.getByRole('button', { name: 'الأسراب' }))
    expect(onNavigate).toHaveBeenCalledWith('teams')
  })
})
