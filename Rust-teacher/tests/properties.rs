//! Propiedades del dominio y del repositorio.

#![allow(clippy::expect_used, clippy::unwrap_used)]

use proptest::prelude::*;
use rust_teacher::domain::{Task, TaskRepositoryPort};
use rust_teacher::infrastructure::memory::InMemoryTaskRepository;

proptest! {
    #[test]
    fn conserva_el_titulo(title in "[a-zA-Z0-9 ]{1,40}") {
        prop_assume!(!title.trim().is_empty());

        let task = Task::new(1, &title, false).unwrap();

        prop_assert_eq!(title, task.title());
    }

    #[test]
    fn los_ids_son_unicos(cantidad in 1usize..50) {
        let repository = InMemoryTaskRepository::default();
        let mut ids = std::collections::HashSet::new();

        for _ in 0..cantidad {
            ids.insert(repository.create("tarea").unwrap().id());
        }

        prop_assert_eq!(cantidad, ids.len());
    }
}
