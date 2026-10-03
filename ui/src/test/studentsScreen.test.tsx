/**
 * شاشة الطلاب — و-٢١ · @covers ق-٢٧٧
 *
 * **الفحص على الثابت الأمنيّ لا على التخطيط:** الرمز يُعرض **مرّةً واحدة**
 * بعد الإنشاء، ولا يظهر في أيّ قراءة. وظهورُه في جدول السجلّ يحوّل أيّ لقطةِ
 * شاشةٍ أو XSS إلى تسريب حسابات — فهو العقد الذي يستحقّ اختبارًا.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { RosterList } from '../api/types/roster'
import type { Teams } from '../api/types/teams'

const roster: RosterList = {
  students: [
    {
      id: 1,
      full_name: 'سالم العتيبي',
      student_no: '1002',
      role: 'pilot',
      team_name: 'سرب الفرقان',
      is_active: true,
    },
    {
      id: 2,
      full_name: 'فهد الدوسري',
      student_no: '1004',
      role: 'pilot',
      team_name: null,
      is_active: false,
    },
  ],
}

const teams: Teams = {
  teams: [
    { id: 1, name: 'سرب الفرقان', code: 'FRQ', archived_at: null, active_members: 1, members: [] },
  ],
}

const createStudent = vi.fn()
const createStudentsBulk = vi.fn()

vi.mock('../api', () => ({
  api: {
    admin: {
      roster: () => Promise.resolve(roster),
      teams: () => Promise.resolve(teams),
      createStudent: (...args: unknown[]) => createStudent(...args),
      createStudentsBulk: (...args: unknown[]) => createStudentsBulk(...args),
      resetPin: () => Promise.resolve({ pin: '5566' }),
      setStudentRole: () => Promise.resolve({ id: 1, role: 'admin' }),
      setStudentActive: () => Promise.resolve({ id: 1, is_active: false }),
    },
  },
  ApiError: class extends Error {},
}))

afterEach(cleanup)

const load = async () => {
  const { default: Screen } = await import('../screens/admin/Students')
  render(<Screen />)
  await waitFor(() => expect(screen.getByText('سالم العتيبي')).toBeInTheDocument())
}

describe('شاشة الطلاب', () => {
  it('**المعطَّل معروضٌ مُعلَّمًا لا مخفيًّا** — وإلّا لم يُعَد تفعيله أبدًا', async () => {
    await load()
    expect(screen.getByText('فهد الدوسري')).toBeInTheDocument()
    expect(screen.getByText('معطَّل')).toBeInTheDocument()
    // ومن لا سرب له يظهر بلا سرب لا يختفي من السجلّ.
    expect(screen.getByText('بلا سرب')).toBeInTheDocument()
  })

  /**
   * «لا رمز في أيّ قراءة» يحرسه الخادم (`test_admin_roster.py`) والنوع
   * (`RosterRow` بلا حقل رمز) — ومحاولةُ فحصه هنا بـ`queryByText(/الرمز/)`
   * كانت تمسك نصّ النموذج التوضيحيّ نفسه، فحصٌ يفشل بلا عطل.
   *
   * وما تملكه هذه الشاشة فعلًا هو **إظهار الرمز الجديد في مكانه**: كانت
   * إعادة التعيين في شاشة التقرير وحدها (و-١٧)، وهي صفةُ طالبٍ لا تقرير.
   */
  it('إعادة التعيين تُظهر الرمز الجديد في صفّه، موسومًا بأنه لمرّة', async () => {
    await load()
    fireEvent.click(screen.getAllByRole('button', { name: 'رمز جديد' })[0]!)
    await waitFor(() => expect(screen.getByText('5566')).toBeInTheDocument())
    expect(screen.getByText(/لا يُعرض مرّة أخرى/)).toBeInTheDocument()
  })

  it('الرمز الصادر يُعرض مرّةً بعد الإضافة، ويختفي بالإغلاق', async () => {
    createStudent.mockResolvedValue({
      id: 9,
      full_name: 'طالب جديد',
      student_no: '2001',
      pin: '4242',
    })
    await load()

    fireEvent.change(screen.getByLabelText('السرب'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('الاسم'), { target: { value: 'طالب جديد' } })
    fireEvent.change(screen.getByLabelText("رقم الطالب — به يدخل"), { target: { value: '2001' } })
    fireEvent.click(screen.getByRole('button', { name: 'إضافة طالب' }))

    await waitFor(() => expect(screen.getByText('4242')).toBeInTheDocument())

    // **لا يُغلَق بنفسه:** هذه الفرصة الوحيدة لقراءة الرمز، فإغلاقٌ تلقائيّ
    // أو تحديثٌ يمحوه يعني حسابًا لا يستطيع صاحبه الدخول إليه.
    fireEvent.click(screen.getByRole('button', { name: 'نسختُها — إغلاق' }))
    await waitFor(() => expect(screen.queryByText('4242')).not.toBeInTheDocument())
  })

  it('اللصقة ترسل سطرًا لكل طالب، وتقبل الفاصلة والتبويب', async () => {
    createStudentsBulk.mockResolvedValue({ created: [], failed: [] })
    await load()

    fireEvent.change(screen.getByLabelText('السرب'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText(/سطر لكل طالب/), {
      target: { value: 'أوّل, 3001\nثانٍ\t3002\n\n  \n' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'إضافة القائمة' }))

    await waitFor(() => expect(createStudentsBulk).toHaveBeenCalled())
    expect(createStudentsBulk).toHaveBeenCalledWith('1', [
      { full_name: 'أوّل', student_no: '3001' },
      { full_name: 'ثانٍ', student_no: '3002' },
    ])
  })

  it('السطر الفاشل يُعرض ولا يُسقط الناجح', async () => {
    createStudentsBulk.mockResolvedValue({
      created: [{ id: 9, full_name: 'أوّل', student_no: '3001', pin: '1111' }],
      failed: [{ line: 2, message: 'رقم الطالب 1002 مستعمل أصلًا.' }],
    })
    await load()

    fireEvent.change(screen.getByLabelText('السرب'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText(/سطر لكل طالب/), {
      target: { value: 'أوّل, 3001\nمكرَّر, 1002' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'إضافة القائمة' }))

    // الرموز الصادرة تُعرض أوّلًا — ثم تظهر السطور الفاشلة بعد إغلاقها.
    await waitFor(() => expect(screen.getByText('1111')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'نسختُها — إغلاق' }))
    await waitFor(() => expect(screen.getByText(/السطر 2/)).toBeInTheDocument())
  })
})
