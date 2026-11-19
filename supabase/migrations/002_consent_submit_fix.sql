create or replace function public.submit_consent_with_audit(
    p_payload jsonb,
    p_request_id text default null
)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
    new_id bigint;
begin
    insert into public.consent_submissions (
        child_first_name,
        child_last_initial,
        child_year_group,
        parent_name,
        parent_email,
        parent_phone,
        emergency_contact,
        medical_notes,
        medical_consent,
        ai_tools_consent,
        signature_name,
        signed_date,
        file_name,
        storage_path,
        created_at
    )
    values (
        p_payload->>'child_first_name',
        p_payload->>'child_last_initial',
        p_payload->>'child_year_group',
        p_payload->>'parent_name',
        p_payload->>'parent_email',
        p_payload->>'parent_phone',
        p_payload->>'emergency_contact',
        p_payload->>'medical_notes',
        coalesce(p_payload->>'medical_consent', 'no'),
        coalesce(p_payload->>'ai_tools_consent', 'no'),
        p_payload->>'signature_name',
        p_payload->>'signed_date',
        p_payload->>'file_name',
        p_payload->>'storage_path',
        coalesce(
            (p_payload->>'created_at')::timestamptz,
            now()
        )
    )
    returning id into new_id;

    insert into public.audit_events (
        actor_id,
        action,
        resource_type,
        resource_id,
        outcome,
        request_id
    )
    values (
        null,
        'consent.submitted',
        'consent_submission',
        new_id::text,
        'success',
        p_request_id
    );

    return new_id;
end;
$$;

revoke all on function public.submit_consent_with_audit(jsonb, text)
from public, anon, authenticated;

grant execute on function public.submit_consent_with_audit(jsonb, text)
to service_role;