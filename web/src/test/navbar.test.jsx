import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import NavBar from '../components/NavBar'

/*
  و-٩أ — اختبار معزول لا عبر `App.jsx`: يثبت أن استخراج `NavBar` من
  `PilotDeck.jsx` لم يغيّر السلوك، بمعزل عن بقية الشاشة.
*/

describe('NavBar — و-٩أ', () => {
  it('طيّار (isAdmin=false) يرى تسعة أزرار فقط', () => {
    render(<NavBar isAdmin={false} onNavigate={() => {}} />)
    expect(screen.getByRole('button', { name: 'قراءاتي' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'محطة التزوّد' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'صدارة الأفراد' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'صدارة الأسراب' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'مشهد التشكيل' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'سؤال اليوم' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'طيار الأسبوع' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'أرسل ملاحظة' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'تحضير القراءة' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'الأوزان' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(9)
  })

  it('مشرف (isAdmin=true) يرى الأزرار الأربعة والعشرين كلّها', () => {
    render(<NavBar isAdmin={true} onNavigate={() => {}} />)
    expect(screen.getAllByRole('button')).toHaveLength(24)
    for (const label of [
      'قراءاتي', 'محطة التزوّد', 'صدارة الأفراد', 'صدارة الأسراب', 'مشهد التشكيل',
      'سؤال اليوم', 'طيار الأسبوع', 'أرسل ملاحظة', 'تحضير القراءة',
      'طابور القراءات', 'التقرير الدوري',
      'الأوزان', 'العتبات', 'الأسراب', 'سجلّ التغييرات',
      'أنشطة الوقود', 'تقييم نشاط', 'الملاحظات', 'اختيار طيار الأسبوع', 'الحضور',
      'التصحيح والتعديل القرآني', 'استيراد راصد', 'طابور تحضير القراءة', 'تقرير تحضير القراءة',
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
